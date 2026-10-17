"""Background execution for long-running agent work (research, coding, test runs).

Work runs in a worker thread, not in the HTTP request. Every event it yields is
buffered with a sequence number, and HTTP clients *watch* a job over SSE:

    POST /api/processes/<pid>/pdd/research     -> starts a job, streams its events
    GET  /api/processes/<pid>/jobs/<job_id>/events?after=<n>
                                               -> re-attach after a disconnect

Closing the browser no longer cancels the work. Each SSE message carries an ``id:``
(the event's sequence number), so clients can resume with ``?after=`` or the standard
``Last-Event-ID`` header. The first event of every stream is ``{"type": "job", "job_id": ...}``.

Event buffers live in process memory. Run the backend with a single worker process
(the default for ``run.py`` and the Docker image) so watchers reach the job's process;
job status itself is persisted in the ``jobs`` table.
"""

import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from .extensions import get_db
from .models import Job
from .utils.sse import sse_event, sse_response

MAX_WORKERS = 4
MAX_RETAINED_JOBS = 100
HEARTBEAT_SECONDS = 15


class _JobBuffer:
    def __init__(self):
        self.events = []
        self.done = False
        self.cond = threading.Condition()

    def append(self, event):
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def finish(self):
        with self.cond:
            self.done = True
            self.cond.notify_all()


class JobRunner:
    def __init__(self, max_workers=MAX_WORKERS):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='okw-job')
        self._buffers = OrderedDict()
        self._lock = threading.Lock()

    def submit(self, app, *, process_id, job_type, work, target_id=None, progress=None) -> str:
        """Start ``work()`` (a generator of event dicts) in the background; return the job id.

        ``progress(event)`` may return ``(pct, message)`` to record progress on the Job row.
        """
        db = get_db()
        job = Job(process_id=process_id, job_type=job_type, status='queued', target_id=target_id)
        db.add(job)
        db.commit()
        job_id = str(job.id)

        buffer = _JobBuffer()
        buffer.append({'type': 'job', 'job_id': job_id, 'job_type': job_type})
        with self._lock:
            self._buffers[job_id] = buffer
            while len(self._buffers) > MAX_RETAINED_JOBS:
                self._buffers.popitem(last=False)

        self._executor.submit(self._run, app, job_id, work, buffer, progress)
        return job_id

    def _run(self, app, job_id, work, buffer, progress):
        with app.app_context():
            self._update(job_id, 'start')
            try:
                for event in work():
                    buffer.append(event)
                    update = progress(event) if progress else None
                    if update:
                        self._update(job_id, 'update_progress', *update)
                    if event.get('type') == 'error':
                        self._update(job_id, 'fail', str(event.get('error', 'error')))
                self._update(job_id, 'complete')
            except Exception as e:  # report, never crash the worker
                buffer.append({'type': 'error', 'error': str(e)})
                self._update(job_id, 'fail', str(e))
            finally:
                buffer.finish()

    @staticmethod
    def _update(job_id, method, *args):
        """Call a Job state method (start/update_progress/fail/complete) and commit."""
        db = get_db()
        job = db.query(Job).filter_by(id=job_id).first()
        if not job or (method == 'complete' and job.status != 'running'):
            return
        getattr(job, method)(*args)
        db.commit()

    def has_buffer(self, job_id) -> bool:
        return job_id in self._buffers

    def events(self, job_id, after=-1, heartbeat=HEARTBEAT_SECONDS):
        """Yield ``(seq, event)`` for events with seq > after, until the job finishes.

        Yields ``(None, None)`` as a keep-alive when nothing happens for ``heartbeat`` seconds.
        """
        buffer = self._buffers.get(job_id)
        if buffer is None:
            return
        next_seq = after + 1
        while True:
            with buffer.cond:
                if next_seq >= len(buffer.events) and not buffer.done:
                    buffer.cond.wait(timeout=heartbeat)
                pending = buffer.events[next_seq:]
                done = buffer.done
            if not pending and not done:
                yield None, None
                continue
            for event in pending:
                yield next_seq, event
                next_seq += 1
            if done and next_seq >= len(buffer.events):
                return

    def stream(self, job_id, after=-1):
        """Flask SSE response that watches a job."""

        def generate():
            for seq, event in self.events(job_id, after):
                if seq is None:
                    yield ': keep-alive\n\n'
                else:
                    yield sse_event(event, event_id=seq)

        return sse_response(generate())

    def wait(self, job_id, timeout=30.0) -> bool:
        """Block until the job's event stream is finished (used by tests and scripts)."""
        buffer = self._buffers.get(job_id)
        if buffer is None:
            return False
        deadline = time.time() + timeout
        with buffer.cond:
            while not buffer.done:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return False
                buffer.cond.wait(timeout=remaining)
        return True


runner = JobRunner()
