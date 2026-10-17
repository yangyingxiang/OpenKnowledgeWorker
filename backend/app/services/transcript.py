"""Transcript recording service — persists agent interactions for debugging and observability."""

from ..extensions import get_db
from ..models.transcript import Transcript


class TranscriptRecorder:
    """Records agent interactions within a session.

    Usage:
        recorder = TranscriptRecorder(process_id, session_key)
        recorder.record_model_request(messages, system_prompt, model)
        recorder.record_model_response(text, tool_uses, usage, duration_ms, stop_reason)
        recorder.record_tool_call(name, input_data)
        recorder.record_tool_result(name, output)
    """

    def __init__(self, process_id: str, session_key: str):
        self.process_id = process_id
        self.session_key = session_key
        self._sequence = 0

    def _next_seq(self) -> int:
        self._sequence += 1
        return self._sequence

    def record_model_request(self, messages: list, system_prompt: str = None, model: str = None):
        """Record an outgoing model API request."""
        db = get_db()
        # Summarize messages to avoid storing huge payloads
        msg_summary = []
        for m in messages[-3:]:  # last 3 messages for context
            role = m.get('role', '?')
            content = m.get('content', '')
            if isinstance(content, list):
                text_parts = [
                    c.get('text', '')[:200] for c in content if isinstance(c, dict) and c.get('type') == 'text'
                ]
                tool_parts = [c.get('name', '') for c in content if isinstance(c, dict) and c.get('type') == 'tool_use']
                content = '; '.join(text_parts + [f'[tool_use:{n}]' for n in tool_parts])
            elif isinstance(content, str):
                content = content[:500]
            msg_summary.append(f'{role}: {content}')

        entry = Transcript(
            process_id=self.process_id,
            session_key=self.session_key,
            sequence=self._next_seq(),
            entry_type='model_request',
            role='user',
            model=model,
            content='\n'.join(msg_summary),
            metadata_={'message_count': len(messages), 'has_system': bool(system_prompt)},
        )
        db.add(entry)
        db.commit()

    def record_model_response(
        self, text: str, tool_uses: list = None, usage: dict = None, duration_ms: float = None, stop_reason: str = None
    ):
        """Record a model API response."""
        db = get_db()
        meta = {'stop_reason': stop_reason}
        if tool_uses:
            meta['tool_calls'] = [tu.get('name', '?') for tu in tool_uses]

        entry = Transcript(
            process_id=self.process_id,
            session_key=self.session_key,
            sequence=self._next_seq(),
            entry_type='model_response',
            role='assistant',
            content=text[:5000] if text else None,
            token_input=usage.get('input_tokens') if usage else None,
            token_output=usage.get('output_tokens') if usage else None,
            duration_ms=duration_ms,
            metadata_=meta,
        )
        db.add(entry)
        db.commit()

    def record_tool_call(self, name: str, input_data: dict):
        """Record a tool invocation."""
        db = get_db()
        # Truncate large inputs (e.g. file content)
        safe_input = {}
        for k, v in (input_data or {}).items():
            if isinstance(v, str) and len(v) > 1000:
                safe_input[k] = v[:1000] + f'... ({len(v)} chars)'
            else:
                safe_input[k] = v

        entry = Transcript(
            process_id=self.process_id,
            session_key=self.session_key,
            sequence=self._next_seq(),
            entry_type='tool_call',
            tool_name=name,
            tool_input=safe_input,
        )
        db.add(entry)
        db.commit()

    def record_tool_result(self, name: str, output: str, duration_ms: float = None):
        """Record a tool execution result."""
        db = get_db()
        entry = Transcript(
            process_id=self.process_id,
            session_key=self.session_key,
            sequence=self._next_seq(),
            entry_type='tool_result',
            tool_name=name,
            tool_output=output[:10000] if output and len(output) > 10000 else output,
            duration_ms=duration_ms,
        )
        db.add(entry)
        db.commit()

    def record_error(self, error: str, context: str = None):
        """Record an error event."""
        db = get_db()
        entry = Transcript(
            process_id=self.process_id,
            session_key=self.session_key,
            sequence=self._next_seq(),
            entry_type='error',
            content=error[:5000] if error else None,
            metadata_={'context': context} if context else None,
        )
        db.add(entry)
        db.commit()


def get_transcript(process_id: str, session_key: str, limit: int = 200, offset: int = 0) -> list[dict]:
    """Retrieve transcript entries for a session."""
    db = get_db()
    entries = (
        db.query(Transcript)
        .filter_by(
            process_id=process_id,
            session_key=session_key,
        )
        .order_by(Transcript.sequence)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [e.to_dict() for e in entries]


def get_transcript_summary(process_id: str, session_key: str) -> dict:
    """Get a summary of a transcript session."""
    db = get_db()
    entries = (
        db.query(Transcript)
        .filter_by(
            process_id=process_id,
            session_key=session_key,
        )
        .order_by(Transcript.sequence)
        .all()
    )

    if not entries:
        return {'session_key': session_key, 'entry_count': 0}

    model_requests = [e for e in entries if e.entry_type == 'model_request']
    model_responses = [e for e in entries if e.entry_type == 'model_response']
    tool_calls = [e for e in entries if e.entry_type == 'tool_call']
    errors = [e for e in entries if e.entry_type == 'error']

    total_input_tokens = sum(e.token_input or 0 for e in model_responses)
    total_output_tokens = sum(e.token_output or 0 for e in model_responses)
    total_duration = sum(e.duration_ms or 0 for e in entries)

    tool_names = {}
    for e in tool_calls:
        tool_names[e.tool_name] = tool_names.get(e.tool_name, 0) + 1

    return {
        'session_key': session_key,
        'entry_count': len(entries),
        'model_requests': len(model_requests),
        'model_responses': len(model_responses),
        'tool_calls': len(tool_calls),
        'errors': len(errors),
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'total_duration_ms': total_duration,
        'tool_usage': tool_names,
        'started_at': entries[0].created_at.isoformat() if entries else None,
        'ended_at': entries[-1].created_at.isoformat() if entries else None,
    }


def list_sessions(process_id: str) -> list[dict]:
    """List all transcript sessions for a process."""
    db = get_db()
    from sqlalchemy import func

    results = (
        db.query(
            Transcript.session_key,
            func.count(Transcript.id).label('entry_count'),
            func.min(Transcript.created_at).label('started_at'),
            func.max(Transcript.created_at).label('ended_at'),
        )
        .filter_by(
            process_id=process_id,
        )
        .group_by(
            Transcript.session_key,
        )
        .order_by(
            func.max(Transcript.created_at).desc(),
        )
        .all()
    )

    return [
        {
            'session_key': r.session_key,
            'entry_count': r.entry_count,
            'started_at': r.started_at.isoformat() if r.started_at else None,
            'ended_at': r.ended_at.isoformat() if r.ended_at else None,
        }
        for r in results
    ]
