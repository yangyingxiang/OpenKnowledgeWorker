from flask import Blueprint, jsonify, request

from ..extensions import get_db
from ..models import KnowledgeItem, PddVersion, Question

questions_bp = Blueprint('questions', __name__)


@questions_bp.route('/<process_id>/questions', methods=['GET'])
def list_questions(process_id):
    db = get_db()
    status = request.args.get('status')
    query = db.query(Question).filter_by(process_id=process_id)
    if status:
        query = query.filter_by(status=status)
    questions = query.order_by(Question.priority, Question.created_at).all()
    return jsonify([q.to_dict() for q in questions])


@questions_bp.route('/<process_id>/questions', methods=['POST'])
def create_question(process_id):
    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'error': 'text is required'}), 400

    db = get_db()
    count = db.query(Question).filter_by(process_id=process_id).count()
    q = Question(
        process_id=process_id,
        display_id=f'Q-{count + 1:04d}',
        text=data['text'],
        priority=data.get('priority', 2),
        target_roles=data.get('target_roles', ['SME']),
        related_pdd_section=data.get('related_pdd_section'),
    )
    db.add(q)
    db.commit()
    return jsonify(q.to_dict()), 201


@questions_bp.route('/<process_id>/questions/<question_id>', methods=['DELETE'])
def delete_question(process_id, question_id):
    db = get_db()
    q = db.query(Question).filter_by(id=question_id, process_id=process_id).first()
    if not q:
        return jsonify({'error': 'Question not found'}), 404
    db.delete(q)
    db.commit()
    return jsonify({'success': True})


@questions_bp.route('/<process_id>/questions/<question_id>', methods=['PUT'])
def update_question(process_id, question_id):
    db = get_db()
    q = db.query(Question).filter_by(id=question_id, process_id=process_id).first()
    if not q:
        return jsonify({'error': 'Question not found'}), 404

    data = request.get_json() or {}
    for field in ['text', 'priority', 'status', 'answer', 'target_roles', 'related_pdd_section']:
        if field in data:
            setattr(q, field, data[field])
    db.commit()
    return jsonify(q.to_dict())


@questions_bp.route('/<process_id>/questions/reset-all', methods=['POST'])
def reset_all_questions(process_id):
    db = get_db()

    # 1. Reset all questions to OPEN with no answer
    questions_reset = db.query(Question).filter_by(process_id=process_id).update({'status': 'OPEN', 'answer': None})

    # 2. Delete all conversation-sourced knowledge items
    knowledge_deleted = db.query(KnowledgeItem).filter_by(process_id=process_id, source_type='conversation').delete()

    # 3. Revert PDD to the last research-sourced version
    pdd_reverted = False
    latest_research = (
        db.query(PddVersion)
        .filter_by(process_id=process_id, change_source='research')
        .order_by(PddVersion.version_number.desc())
        .first()
    )
    if latest_research:
        # Check if there are newer versions with change_source='chat'
        newer_chat_versions = (
            db.query(PddVersion)
            .filter_by(process_id=process_id, change_source='chat')
            .filter(PddVersion.version_number > latest_research.version_number)
            .count()
        )
        if newer_chat_versions > 0:
            # Find the current max version number
            max_version = (
                db.query(PddVersion.version_number)
                .filter_by(process_id=process_id)
                .order_by(PddVersion.version_number.desc())
                .first()
            )
            new_version_number = (max_version[0] + 1) if max_version else 1
            reverted = PddVersion(
                process_id=process_id,
                version_number=new_version_number,
                content=latest_research.content,
                change_summary='Reverted to last research-sourced version',
                change_source='research',
                parent_version_id=latest_research.id,
            )
            db.add(reverted)
            pdd_reverted = True

    db.commit()

    return jsonify(
        {
            'success': True,
            'questions_reset': questions_reset,
            'knowledge_deleted': knowledge_deleted,
            'pdd_reverted': pdd_reverted,
        }
    )
