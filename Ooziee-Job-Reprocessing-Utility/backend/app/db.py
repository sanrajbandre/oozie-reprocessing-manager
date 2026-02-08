from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .settings import settings

class Base(DeclarativeBase):
    pass

def build_engine(db_url: str):
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    try:
        parsed = make_url(db_url)
    except Exception:
        parsed = None

    if parsed and parsed.get_backend_name() == "mysql":
        engine_kwargs.update(
            {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 30,
            }
        )
        if not parsed.query.get("charset"):
            engine_kwargs["connect_args"] = {"charset": "utf8mb4"}

    return create_engine(db_url, **engine_kwargs)


engine = build_engine(settings.db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
