"""Transcript API endpoints for viewing agent interaction history."""

from flask import Blueprint, jsonify, request

from ..services.transcript import get_transcript, get_transcript_summary, list_sessions

transcript_bp = Blueprint('transcripts', __name__)


@transcript_bp.route('/<process_id>/transcripts', methods=['GET'])
def list_transcript_sessions(process_id):
    """List all transcript sessions for a process."""
    return jsonify(list_sessions(process_id))


@transcript_bp.route('/<process_id>/transcripts/<session_key>', methods=['GET'])
def get_session_transcript(process_id, session_key):
    """Get transcript entries for a session."""
    limit = request.args.get('limit', 200, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(get_transcript(process_id, session_key, limit, offset))


@transcript_bp.route('/<process_id>/transcripts/<session_key>/summary', methods=['GET'])
def get_session_summary(process_id, session_key):
    """Get a summary of a transcript session (token usage, tool counts, etc.)."""
    return jsonify(get_transcript_summary(process_id, session_key))
