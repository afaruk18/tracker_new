import getpass
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class TrackerSettings(BaseSettings):
    """Settings controlling the behaviour of the activity tracker client."""

    IDLE_THRESHOLD: int = Field(50, description="seconds before user considered idle")
    HEARTBEAT_EVERY: int = Field(60, description="seconds between heartbeat writes")
    SCREENSHOT_INTERVAL: int = Field(86400, description="seconds between automatic screenshots (0 = disabled)")
    IMAGE_FORMAT: str = Field("png", description="png | jpeg")
    IMAGE_QUALITY: int = Field(85, description="JPEG quality when IMAGE_FORMAT == 'jpeg'")
    WINDOW_EVENT_INTERVAL: int = Field(5, description="seconds a window must remain active before it is logged")

    BASE_DIR: Path = Path.cwd() / "tracker"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def screenshot_dir(self) -> Path:
        path = self.BASE_DIR / "screenshots"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def heartbeat_file(self) -> Path:
        return self.BASE_DIR / "heartbeat.txt"

    @property
    def user(self) -> str:
        return getpass.getuser()

    @property
    def system(self) -> str:
        return sys.platform


tracker_settings = TrackerSettings()
