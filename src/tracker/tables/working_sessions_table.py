from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class WorkingSession(SQLModel, table=True):
    """Database model representing a continuous working session delimited by
    an *Active* event at the beginning and an *Inactive* (or shutdown) event at
    the end.  The *end_time* column is ``NULL`` while the session is still
    ongoing and filled in once the end is known."""

    __table_args__ = (UniqueConstraint("username", "start_time", name="ux_working_session_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    start_time: datetime = Field(index=True, description="Timestamp when the session started")
    end_time: datetime | None = Field(
        default=None,
        index=True,
        description="Timestamp when the session ended – NULL while ongoing",
    )
    end_reason: str | None = Field(
        default=None,
        description="Reason the session ended (Inactive, Screen Locked, Shutdown, Started)",
    )
