from datetime import datetime

from sqlmodel import Field, SQLModel


class HeartbeatEvent(SQLModel, table=True):
    """Database model for periodic heartbeat pings indicating the tracker is alive."""

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, description="System user that emitted the heartbeat")
    timestamp: datetime = Field(index=True, description="Timestamp of the heartbeat event")
    status: str = Field(default="Alive", description="Heartbeat status text")
