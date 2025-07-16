from contextlib import contextmanager
from typing import Generator

from loguru import logger
from sqlmodel import Session, SQLModel, create_engine, text

from tracker.config.db_settings import db_settings
from tracker.tables.activity_table import ActivityEvent
from tracker.tables.adk_query_table import AdkQuery
from tracker.tables.heartbeat_table import HeartbeatEvent
from tracker.tables.people_table import Person_Usernames
from tracker.tables.window_event_table import WindowEvent
from tracker.tables.working_sessions_table import WorkingSession

# Initialize database engine
_engine = create_engine(db_settings.database_url, echo=False)

# Create all tables
SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        Session: SQLModel database session
    """
    with Session(_engine) as session:
        yield session


def test_database_connection() -> bool:
    """Test database connection and return True if successful, False otherwise.

    Returns:
        bool: True if database connection is successful, False otherwise
    """
    try:
        with Session(_engine) as session:
            # Try to execute a simple query to test the connection
            result = session.exec(text("SELECT 1"))
            result.fetchone()
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
