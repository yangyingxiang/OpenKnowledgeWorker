def apply_security_headers(app):
    frontend_url = app.config['FRONTEND_URL']

    @app.after_request
    def add_security_headers(response):
        from flask import request

        # Allow framing for document content previews from the frontend
        is_doc_content = '/documents/' in request.path and request.path.endswith('/content')
        if not is_doc_content:
            response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), payment=(), usb=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "connect-src 'self' https://api.anthropic.com; "
            "script-src 'self' 'unsafe-inline'; "
            f"style-src 'self' 'unsafe-inline'; "
            f"frame-ancestors 'self' {frontend_url}"
        )
        return response
