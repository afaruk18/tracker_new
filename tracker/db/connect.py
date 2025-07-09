from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from tracker.config.db_settings import db_settings
from tracker.tables.activity_table import ActivityEvent
from tracker.tables.heartbeat_table import HeartbeatEvent

_engine = create_engine(db_settings.database_url, echo=False)
SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel session bound to the shared engine.

    Usage::

        with get_session() as session:
            session.add(obj)
            session.commit()
    """
    with Session(_engine) as session:
        yield session
