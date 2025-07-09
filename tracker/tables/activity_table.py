from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class ActivityEvent(SQLModel, table=True):
    """Database model describing a single activity event."""

    __table_args__ = (UniqueConstraint("username", "timestamp", "event", name="ux_activity_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    event: str = Field(index=True)
