"""Background job status and resumable event streams (see app/jobs.py)."""

from flask import Blueprint, jsonify, request

from ..extensions import get_db
from ..jobs import runner
from ..models import Job

jobs_bp = Blueprint('jobs', __name__)
job_events_bp = Blueprint('job_events', __name__)


@jobs_bp.route('/<process_id>/jobs', methods=['GET'])
def list_jobs(process_id):
    query = get_db().query(Job).filter_by(process_id=process_id)
    job_type = request.args.get('type')
    if job_type:
        query = query.filter_by(job_type=job_type)
    jobs = query.order_by(Job.created_at.desc()).limit(50).all()
    return jsonify([j.to_dict() for j in jobs])


@jobs_bp.route('/<process_id>/jobs/<job_id>', methods=['GET'])
def get_job(process_id, job_id):
    job = get_db().query(Job).filter_by(id=job_id, process_id=process_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({**job.to_dict(), 'streamable': runner.has_buffer(job_id)})


@jobs_bp.route('/<process_id>/jobs/<job_id>/events', methods=['GET'])
def job_events(process_id, job_id):
    """Re-attach to a job's event stream. Resume with ?after=<seq> or Last-Event-ID."""
    job = get_db().query(Job).filter_by(id=job_id, process_id=process_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if not runner.has_buffer(job_id):
        return jsonify({'error': 'Event history is no longer available for this job', 'job': job.to_dict()}), 410
    after = request.args.get('after', request.headers.get('Last-Event-ID', -1))
    try:
        after = int(after)
    except (TypeError, ValueError):
        after = -1
    return runner.stream(job_id, after)


@job_events_bp.route('/<job_id>/events', methods=['GET'])
def job_events_by_id(job_id):
    """Same as ``/api/processes/<pid>/jobs/<job_id>/events``, addressed by job id alone."""
    job = get_db().query(Job).filter_by(id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return job_events(str(job.process_id), job_id)
