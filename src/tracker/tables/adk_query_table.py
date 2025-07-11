from sqlmodel import Field, SQLModel, UniqueConstraint


class AdkQuery(SQLModel, table=True):
    """Database model representing a reusable ADK query saved by the user.

    The *query* column stores the full ADK query text while *tags* holds
    a comma-separated set of keywords (e.g. "activity,calendar,performance")
    that makes searching and categorising easier.
    """

    __table_args__ = (
        UniqueConstraint("name", name="ux_adk_query_name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Human-readable name/title of the saved query")
    query: str = Field(description="Raw ADK query string")
    tags: str | None = Field(default=None, index=True, description="Comma-separated list of tags for quick lookup")