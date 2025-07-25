from sqlmodel import Field, SQLModel, UniqueConstraint


class Person_Usernames(SQLModel, table=True):
    """Database model describing a single person and usernames in external systems."""

    __table_args__ = (
        UniqueConstraint("github_user", name="ux_person_github"),
        UniqueConstraint("jira_user", name="ux_person_jira"),
        UniqueConstraint("gcal_user", name="ux_person_gcal"),
        UniqueConstraint("computer_user", name="ux_person_computer"),
    )

    # Primary key
    person_id: int | None = Field(default=None, primary_key=True)

    # Basic identity
    full_name: str = Field(index=True, description="Full legal name of the person")
    preferred_name: str | None = Field(default=None, index=True, description="Preferred display name (nick name)")

    # External system usernames (optional because not everyone has all accounts)
    github_user: str | None = Field(default=None, index=True, description="GitHub username")
    jira_user: str | None = Field(default=None, index=True, description="Jira username")
    gcal_user: str | None = Field(default=None, index=True, description="Google Calendar email")
    computer_user: str | None = Field(default=None, index=True, description="Local computer (OS) account username")