from app.jobs import JobRunner
from app.models import Job


def test_job_events_are_buffered_and_resumable(app, db_session, process_id):
    runner = JobRunner(max_workers=1)

    def work():
        yield {'type': 'status', 'status': 'working'}
        yield {'type': 'done'}

    with app.app_context():
        job_id = runner.submit(
            app,
            process_id=process_id,
            job_type='research',
            work=work,
            progress=lambda e: (50, 'half') if e.get('type') == 'status' else None,
        )
        assert runner.wait(job_id, timeout=10)
        events = list(runner.events(job_id))
        assert [e['type'] for _, e in events] == ['job', 'status', 'done']
        assert [seq for seq, _ in runner.events(job_id, after=1)] == [2]
        db_session.expire_all()
        assert db_session.query(Job).filter_by(id=job_id).one().status == 'completed'


def test_failing_job_is_marked_failed(app, db_session, process_id):
    runner = JobRunner(max_workers=1)

    def work():
        yield {'type': 'status'}
        raise RuntimeError('kaboom')

    with app.app_context():
        job_id = runner.submit(app, process_id=process_id, job_type='coding', work=work)
        runner.wait(job_id, timeout=10)
        assert list(runner.events(job_id))[-1][1] == {'type': 'error', 'error': 'kaboom'}
        db_session.expire_all()
        job = db_session.query(Job).filter_by(id=job_id).one()
        assert job.status == 'failed' and job.error_message == 'kaboom'
