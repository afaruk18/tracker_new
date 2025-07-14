from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel, UniqueConstraint


class ActivityEventType(StrEnum):
    STARTED = "System Started"
    STOPPED = "System Stopped"
    SCREEN_LOCKED = "Screen Locked"
    SCREEN_UNLOCKED = "Screen Unlocked"
    ACTIVE = "User Active"
    INACTIVE = "User Inactive"
    UNSUPPORTED = "Unsupported Platform"
    USER_INTERRUPT = "User Interrupt"
    NORMAL_SHUTDOWN = "Normal Shutdown"
    SYSTEM_SHUTDOWN = "Shutdown Signal Received"


class ActivityEvent(SQLModel, table=True):
    """Database model describing a single activity event."""

    __table_args__ = (UniqueConstraint("username", "timestamp", "event", name="ux_activity_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    event: str = Field(index=True)
