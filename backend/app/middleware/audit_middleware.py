import hashlib

from flask import g, request

from ..extensions import get_db
from ..models.audit_log import AuditLog


def apply_audit_middleware(app):
    @app.after_request
    def audit_log(response):
        # Skip non-API, CORS preflight, health checks, and GET reads to reduce DB churn.
        if (
            not request.path.startswith('/api/')
            or request.method == 'OPTIONS'
            or request.path == '/health'
            or (request.method == 'GET' and response.status_code < 300)
        ):
            return response

        try:
            session = get_db()
            body_hash = None
            if request.data:
                body_hash = hashlib.sha256(request.data).hexdigest()

            action = f"{request.method.lower()}:{request.path}"
            entry = AuditLog(
                action=action,
                entity_type=getattr(g, 'audit_entity_type', None),
                entity_id=getattr(g, 'audit_entity_id', None),
                actor='system',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:500] if request.user_agent.string else None,
                request_method=request.method,
                request_path=request.path[:1024],
                response_status=response.status_code,
                detail={'body_hash': body_hash} if body_hash else None,
            )
            session.add(entry)
            session.commit()
        except Exception:
            pass  # Audit logging should never break the request
        return response
