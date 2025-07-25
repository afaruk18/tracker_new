from pydantic import Field
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    """Application database connection settings."""
    PG_USER:     str = Field("afaruk",        env="PG_USER")
    PG_PASS:     str = Field("158158158",     env="PG_PASS")
    PG_DATABASE: str = Field("last_tracker_db", env="PG_DATABASE")
    PG_HOST:     str = Field("localhost",     env="PG_HOST")
    PG_PORT:     int = Field(5452,            env="PG_PORT")


    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """Return a SQLAlchemy-compatible Postgres connection URL."""
        return f"postgresql+psycopg://{self.PG_USER}:{self.PG_PASS}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"


db_settings = DBSettings()
