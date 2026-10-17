from flask import Blueprint, current_app, jsonify, request

from ..agent.chat_agent import run_agent_streaming
from ..agent.prompts import CHAT_SYSTEM_PROMPT, CODE_CHAT_SYSTEM_PROMPT, TEST_CHAT_SYSTEM_PROMPT
from ..agent.tool_registry import create_process_tools
from ..extensions import get_db
from ..models import ChatMessage, ChatSession, PddVersion
from ..utils.sse import sse_event, sse_response

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/<process_id>/chat/sessions', methods=['GET'])
def list_sessions(process_id):
    db = get_db()
    sessions = db.query(ChatSession).filter_by(process_id=process_id).order_by(ChatSession.updated_at.desc()).all()
    return jsonify([s.to_dict() for s in sessions])


@chat_bp.route('/<process_id>/chat/sessions', methods=['POST'])
def create_session(process_id):
    data = request.get_json() or {}
    db = get_db()
    session = ChatSession(
        process_id=process_id,
        expert_name=data.get('expert_name', 'Domain Expert'),
        expert_role=data.get('expert_role', 'SME'),
        status='active',
    )
    db.add(session)
    db.commit()

    # Add system welcome message
    welcome = ChatMessage(
        session_id=session.id,
        role='system',
        content=f"Chat session started with {session.expert_name} ({session.expert_role}).",
    )
    db.add(welcome)
    db.commit()
    return jsonify(session.to_dict(include_messages=True)), 201


@chat_bp.route('/<process_id>/chat/sessions/<session_id>', methods=['GET'])
def get_session(process_id, session_id):
    db = get_db()
    session = db.query(ChatSession).filter_by(id=session_id, process_id=process_id).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session.to_dict(include_messages=True))


@chat_bp.route('/<process_id>/chat/sessions/<session_id>', methods=['PUT'])
def update_session(process_id, session_id):
    db = get_db()
    session = db.query(ChatSession).filter_by(id=session_id, process_id=process_id).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    data = request.get_json() or {}
    if 'status' in data:
        session.status = data['status']
    if 'expert_name' in data:
        session.expert_name = data['expert_name']
    db.commit()
    return jsonify(session.to_dict())


@chat_bp.route('/<process_id>/chat/sessions/<session_id>/message', methods=['POST'])
def send_message(process_id, session_id):
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'content is required'}), 400

    db = get_db()
    session = db.query(ChatSession).filter_by(id=session_id, process_id=process_id).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session.status != 'active':
        return jsonify({'error': 'Session is not active'}), 400

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role='user',
        content=data['content'],
    )
    db.add(user_msg)
    db.commit()

    # Build message history for LLM
    messages_db = db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()

    llm_messages = []
    for msg in messages_db:
        if msg.role == 'system':
            continue
        llm_messages.append(
            {
                'role': msg.role,
                'content': msg.content,
            }
        )

    # Select system prompt based on page context
    context = data.get('context', 'sop')
    prompt_map = {
        'sop': CHAT_SYSTEM_PROMPT,
        'code': CODE_CHAT_SYSTEM_PROMPT,
        'tests': TEST_CHAT_SYSTEM_PROMPT,
    }
    system_prompt = prompt_map.get(context, CHAT_SYSTEM_PROMPT)

    # Pre-load current PDD so the agent can edit directly without calling read_pdd first
    current_pdd = (
        db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    )
    if current_pdd and current_pdd.content:
        if context == 'code':
            # For code context, include PDD as reference only — agent MUST use code tools
            system_prompt += (
                "\n\n## Current PDD (reference only — do NOT answer code questions from this)\n"
                "The PDD describes the business logic. But the user is on the Code page and "
                "wants to see the ACTUAL CODE. You MUST use list_code_files, read_code_file, "
                "and navigate_to_file to show them the implementation. Never answer questions "
                "about code locations or logic from the PDD alone.\n"
            )
        else:
            system_prompt += (
                "\n\n## Current PDD Content (already loaded — do NOT call read_pdd, "
                "go straight to propose_pdd_edit if changes are needed)\n\n" + current_pdd.content
            )

    tool_registry = create_process_tools(process_id, session_id=session.id)
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            yield sse_event({'type': 'status', 'status': 'started'})
            collected_text = ''
            tool_calls = []
            tool_results = []

            try:
                for event in run_agent_streaming(llm_messages, system_prompt, tool_registry):
                    if event['type'] == 'delta':
                        collected_text += event.get('text', '')
                    elif event['type'] == 'tool_call':
                        tool_calls.append({'name': event['name'], 'input': event['input']})
                    elif event['type'] == 'tool_result':
                        tool_results.append({'name': event['name'], 'result': event['result']})
                    elif event['type'] == 'done':
                        collected_text = event.get('text', collected_text)

                    yield sse_event(event)
            except Exception as e:
                yield sse_event({'type': 'error', 'error': str(e)})

            # Save assistant message
            if collected_text:
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role='assistant',
                    content=collected_text,
                    tool_calls=tool_calls if tool_calls else None,
                    tool_results=tool_results if tool_results else None,
                )
                db_inner = get_db()
                db_inner.add(assistant_msg)
                db_inner.commit()

    return sse_response(generate())
