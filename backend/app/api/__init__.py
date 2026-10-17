def register_blueprints(app):
    from .chat import chat_bp
    from .coding_agent import coding_bp
    from .documents import documents_bp
    from .domain_packs import domain_packs_bp
    from .evidence import evidence_bp
    from .golden_datasets import golden_bp
    from .health import health_bp
    from .jobs import job_events_bp, jobs_bp
    from .knowledge import knowledge_bp
    from .pdd import pdd_bp
    from .processes import processes_bp
    from .questions import questions_bp
    from .test_suite import test_bp
    from .transcripts import transcript_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(processes_bp, url_prefix='/api/processes')
    app.register_blueprint(documents_bp, url_prefix='/api/processes')
    app.register_blueprint(pdd_bp, url_prefix='/api/processes')
    app.register_blueprint(chat_bp, url_prefix='/api/processes')
    app.register_blueprint(knowledge_bp, url_prefix='/api/processes')
    app.register_blueprint(questions_bp, url_prefix='/api/processes')
    app.register_blueprint(coding_bp, url_prefix='/api/processes')
    app.register_blueprint(test_bp, url_prefix='/api/processes')
    app.register_blueprint(evidence_bp, url_prefix='/api/processes')
    app.register_blueprint(golden_bp, url_prefix='/api/processes')
    app.register_blueprint(transcript_bp, url_prefix='/api/processes')
    app.register_blueprint(jobs_bp, url_prefix='/api/processes')
    app.register_blueprint(job_events_bp, url_prefix='/api/jobs')
    app.register_blueprint(domain_packs_bp, url_prefix='/api/domain-packs')
