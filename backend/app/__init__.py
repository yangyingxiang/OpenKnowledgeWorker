import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Load the repository-root .env (one level above backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


def create_app():
    app = Flask(__name__)

    from .config import load_config

    app.config.update(load_config())

    CORS(app, origins=[app.config['FRONTEND_URL']], supports_credentials=True)

    from .middleware.security_headers import apply_security_headers

    apply_security_headers(app)

    from .middleware.audit_middleware import apply_audit_middleware

    apply_audit_middleware(app)

    from .extensions import init_db

    init_db(app)

    from .api import register_blueprints

    register_blueprints(app)

    return app
