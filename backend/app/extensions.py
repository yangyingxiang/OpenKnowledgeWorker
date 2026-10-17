from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

engine = None
SessionLocal = None
db = None


class Base(DeclarativeBase):
    pass


def init_db(app):
    global engine, SessionLocal, db
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
    )
    SessionLocal = scoped_session(sessionmaker(bind=engine))
    db = SessionLocal

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        SessionLocal.remove()


def get_db():
    return SessionLocal()
