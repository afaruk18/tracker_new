from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class HeartbeatType(StrEnum):
    """Enum for heartbeat event types."""

    REGULAR = "REGULAR"
    FINAL = "FINAL"


class HeartbeatEvent(SQLModel, table=True):
    """Database model for periodic heartbeat pings indicating the tracker is alive."""

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, description="System user that emitted the heartbeat")
    timestamp: datetime = Field(index=True, description="Timestamp of the heartbeat event")
    type: HeartbeatType = Field(default=HeartbeatType.REGULAR, description="Type of heartbeat event")
