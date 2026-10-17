from flask import Blueprint, jsonify, request

from ..extensions import get_db
from ..models import KnowledgeItem

knowledge_bp = Blueprint('knowledge', __name__)


@knowledge_bp.route('/<process_id>/knowledge', methods=['GET'])
def list_knowledge(process_id):
    db = get_db()
    items = (
        db.query(KnowledgeItem)
        .filter_by(process_id=process_id)
        .order_by(KnowledgeItem.section, KnowledgeItem.created_at.desc())
        .all()
    )
    return jsonify([i.to_dict() for i in items])


@knowledge_bp.route('/<process_id>/knowledge', methods=['POST'])
def add_knowledge(process_id):
    data = request.get_json()
    if not data or not data.get('section') or not data.get('content'):
        return jsonify({'error': 'section and content are required'}), 400

    db = get_db()
    item = KnowledgeItem(
        process_id=process_id,
        section=data['section'],
        content=data['content'],
        confidence=data.get('confidence', 'TENTATIVE'),
        source_type=data.get('source_type', 'manual'),
        source_detail=data.get('source_detail'),
    )
    db.add(item)
    db.commit()
    return jsonify(item.to_dict()), 201


@knowledge_bp.route('/<process_id>/knowledge/<item_id>', methods=['DELETE'])
def delete_knowledge(process_id, item_id):
    db = get_db()
    item = db.query(KnowledgeItem).filter_by(id=item_id, process_id=process_id).first()
    if not item:
        return jsonify({'error': 'Knowledge item not found'}), 404
    db.delete(item)
    db.commit()
    return jsonify({'success': True})


@knowledge_bp.route('/<process_id>/knowledge/<item_id>', methods=['PUT'])
def update_knowledge(process_id, item_id):
    db = get_db()
    item = db.query(KnowledgeItem).filter_by(id=item_id, process_id=process_id).first()
    if not item:
        return jsonify({'error': 'Knowledge item not found'}), 404

    data = request.get_json() or {}
    for field in ['section', 'content', 'confidence']:
        if field in data:
            setattr(item, field, data[field])
    db.commit()
    return jsonify(item.to_dict())
