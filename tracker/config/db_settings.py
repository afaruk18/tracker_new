from pydantic import Field
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    """Application database connection settings."""

    PG_USER: str = Field(..., env="PG_USER", description="Postgres username")
    PG_PASS: str = Field(..., env="PG_PASS", description="Postgres password")
    PG_DATABASE: str = Field(..., env="PG_DATABASE", description="Postgres database name")
    PG_HOST: str = Field(..., env="PG_HOST", description="Postgres host")
    PG_PORT: str = Field(..., env="PG_PORT", description="Postgres port")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """Return a SQLAlchemy-compatible Postgres connection URL."""
        print(f"postgresql+psycopg://{self.PG_USER}:{self.PG_PASS}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}")
        return f"postgresql+psycopg://{self.PG_USER}:{self.PG_PASS}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"


db_settings = DBSettings()
