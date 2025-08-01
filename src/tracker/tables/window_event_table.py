from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class WindowEvent(SQLModel, table=True):
    """Database model describing a single window event."""

    __table_args__ = (UniqueConstraint("username", "timestamp", "window_title", name="ux_window_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    timestamp: datetime = Field(index=True)  # For backward compatibility (same as start_time)
    window_title: str = Field(index=True)
    duration: float = Field(description="Duration in seconds that the window was focused")
    start_time: datetime | None = Field(default=None, index=True, description="Explicit start timestamp of window focus")
    end_time: datetime | None = Field(default=None, index=True, description="Explicit end timestamp of window focus")
