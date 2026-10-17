"""Multi-file coding agent API endpoints."""

import io
import zipfile

from flask import Blueprint, current_app, jsonify, request, send_file

from ..agent.code_agent_loop import run_coding_agent
from ..extensions import get_db
from ..jobs import runner
from ..models import CodeFile, CodeProject, PddVersion

coding_bp = Blueprint('coding', __name__)


@coding_bp.route('/<process_id>/coding/start', methods=['POST'])
def start_coding_agent(process_id):
    """Start the multi-file coding agent as a background job. Streams its events (SSE)."""
    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    if not pdd:
        return jsonify({'error': 'No PDD exists yet'}), 400

    data = request.get_json() or {}
    max_iterations = data.get('max_iterations', 10)

    project = CodeProject(
        process_id=process_id,
        pdd_version_id=pdd.id,
        status='planning',
        max_iterations=max_iterations,
        agent_log=[],
    )
    db.add(project)
    db.commit()
    return _start_coding_job(process_id, project)


@coding_bp.route('/<process_id>/coding/projects', methods=['GET'])
def list_projects(process_id):
    """List all coding projects for a process."""
    db = get_db()
    projects = db.query(CodeProject).filter_by(process_id=process_id).order_by(CodeProject.created_at.desc()).all()
    return jsonify([p.to_dict() for p in projects])


@coding_bp.route('/<process_id>/coding/projects/<project_id>', methods=['GET'])
def get_project(process_id, project_id):
    """Get a coding project with all its files."""
    db = get_db()
    project = db.query(CodeProject).filter_by(id=project_id, process_id=process_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(project.to_dict_with_files())


@coding_bp.route('/<process_id>/coding/projects/<project_id>/files', methods=['GET'])
def list_project_files(process_id, project_id):
    """List files in a coding project."""
    db = get_db()
    files = db.query(CodeFile).filter_by(project_id=project_id).order_by(CodeFile.file_path).all()
    return jsonify([f.to_summary() for f in files])


@coding_bp.route('/<process_id>/coding/projects/<project_id>/files/<file_id>', methods=['GET'])
def get_project_file(process_id, project_id, file_id):
    """Get a specific file's content."""
    db = get_db()
    cf = db.query(CodeFile).filter_by(id=file_id, project_id=project_id).first()
    if not cf:
        return jsonify({'error': 'File not found'}), 404
    return jsonify(cf.to_dict())


@coding_bp.route('/<process_id>/coding/projects/<project_id>/retry', methods=['POST'])
def retry_project(process_id, project_id):
    """Re-run the coding agent on an existing project (enters fix loop)."""
    db = get_db()
    project = db.query(CodeProject).filter_by(id=project_id, process_id=process_id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    project.status = 'fixing'
    db.commit()
    return _start_coding_job(process_id, project)


@coding_bp.route('/<process_id>/coding/projects/<project_id>/mapping', methods=['GET'])
def get_code_mapping(process_id, project_id):
    """Get code-to-PDD mapping for a project."""
    from ..services.code_mapping import get_code_mapping_summary

    return jsonify(get_code_mapping_summary(project_id))


@coding_bp.route('/<process_id>/coding/projects/<project_id>/mapping/build', methods=['POST'])
def build_code_mapping(process_id, project_id):
    """Extract code units and build PDD mapping for a project."""
    from ..services.code_mapping import extract_code_units

    count = extract_code_units(project_id)
    return jsonify({'units_extracted': count})


@coding_bp.route('/<process_id>/coding/projects/<project_id>/mapping/stale', methods=['GET'])
def check_stale_code(process_id, project_id):
    """Check for stale code units due to PDD changes."""
    from ..services.code_mapping import detect_stale_units

    return jsonify(detect_stale_units(project_id))


@coding_bp.route('/<process_id>/coding/projects/<project_id>/download', methods=['GET'])
def download_project(process_id, project_id):
    """Download all project files as a zip."""
    db = get_db()
    files = db.query(CodeFile).filter_by(project_id=project_id).order_by(CodeFile.file_path).all()
    if not files:
        return jsonify({'error': 'No files in project'}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for cf in files:
            zf.writestr(cf.file_path, cf.content)
    buf.seek(0)

    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=f'engine_{project_id[:8]}.zip')


_PHASE_PROGRESS = {'planning': 10, 'coding': 30, 'testing': 60, 'fixing': 75, 'complete': 99}


def _start_coding_job(process_id, project):
    """Run the coding agent for ``project`` as a background job and stream its events."""
    project_id = str(project.id)

    def progress(event):
        if event.get('type') == 'status':
            phase = event.get('status', '')
            return _PHASE_PROGRESS.get(phase, 50), f'Phase: {phase}'
        return None

    def work():
        try:
            yield from run_coding_agent(process_id, project_id)
        except Exception as e:
            db = get_db()
            proj = db.query(CodeProject).filter_by(id=project_id).first()
            if proj:
                proj.status = 'error'
                proj.agent_log = (proj.agent_log or []) + [{'phase': 'error', 'error': str(e)}]
                db.commit()
            yield {'type': 'error', 'error': str(e)}

    job_id = runner.submit(
        current_app._get_current_object(),
        process_id=process_id,
        job_type='coding',
        work=work,
        target_id=project.id,
        progress=progress,
    )
    return runner.stream(job_id)
