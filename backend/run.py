#!/usr/bin/env python3
"""Entry point for the OpenKnowledgeWorker backend (development server).

For production, run under gunicorn instead, e.g.:
    gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:5003 "app:create_app()"
"""

import os
import sys

# Add the backend directory to the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)
