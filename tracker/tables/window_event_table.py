from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class WindowEvent(SQLModel, table=True):
    """Database model describing a single window event."""

    __table_args__ = (UniqueConstraint("username", "timestamp", "window_title", name="ux_window_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    window_title: str = Field(index=True)
