import json

from flask import Response


def sse_event(data, event_type=None, event_id=None):
    """Format a single SSE event."""
    msg = ''
    if event_id is not None:
        msg += f'id: {event_id}\n'
    if event_type:
        msg += f'event: {event_type}\n'
    msg += f'data: {json.dumps(data, default=str)}\n\n'
    return msg


def sse_response(generator):
    """Create an SSE Response from a generator."""
    return Response(
        generator,
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
