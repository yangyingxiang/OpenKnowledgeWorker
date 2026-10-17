from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import get_db

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health():
    return jsonify({'status': 'ok'})


@health_bp.route('/ready')
def ready():
    try:
        db = get_db()
        db.execute(text('SELECT 1'))
        return jsonify({'status': 'ready', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'not_ready', 'error': str(e)}), 503
