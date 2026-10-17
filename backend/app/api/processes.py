from flask import Blueprint, jsonify, request

from ..extensions import get_db
from ..models import Process

processes_bp = Blueprint('processes', __name__)


@processes_bp.route('', methods=['GET'])
def list_processes():
    db = get_db()
    processes = db.query(Process).filter(Process.status != 'archived').order_by(Process.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in processes])


@processes_bp.route('', methods=['POST'])
def create_process():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    db = get_db()
    process = Process(
        name=data['name'],
        domain=data.get('domain'),
        description=data.get('description'),
        status='draft',
        key_inputs=data.get('key_inputs', []),
        key_outputs=data.get('key_outputs', []),
    )
    db.add(process)
    db.commit()
    return jsonify(process.to_dict()), 201


@processes_bp.route('/<process_id>', methods=['GET'])
def get_process(process_id):
    db = get_db()
    process = db.query(Process).filter_by(id=process_id).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404
    return jsonify(process.to_dict())


@processes_bp.route('/<process_id>', methods=['PUT'])
def update_process(process_id):
    db = get_db()
    process = db.query(Process).filter_by(id=process_id).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404

    data = request.get_json()
    for field in ['name', 'domain', 'description', 'status', 'key_inputs', 'key_outputs']:
        if field in data:
            setattr(process, field, data[field])
    db.commit()
    return jsonify(process.to_dict())


@processes_bp.route('/<process_id>', methods=['DELETE'])
def delete_process(process_id):
    db = get_db()
    process = db.query(Process).filter_by(id=process_id).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404
    process.status = 'archived'
    db.commit()
    return jsonify({'success': True})
