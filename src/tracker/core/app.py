import signal
import time

from loguru import logger

from tracker.config.tracker_settings import tracker_settings
from tracker.core import ActivityStateTask, HeartbeatTask, ScreenshotTask, WindowTrackerTask
from tracker.db.event_store import EventStore
from tracker.tables.activity_table import ActivityEventType


class ActivityTracker:
    SUPPORTED_SYSTEMS: set[str] = {"windows", "darwin", "linux"}
    kill_now = False

    def __init__(self) -> None:
        self.event_store = EventStore()

        self.window_tracker = WindowTrackerTask(interval=tracker_settings.WINDOW_EVENT_INTERVAL)
        self.activity_state_task = ActivityStateTask()
        self.heartbeat_task = HeartbeatTask(interval=tracker_settings.HEARTBEAT_EVERY)
        self.screenshot_task = ScreenshotTask(interval=tracker_settings.SCREENSHOT_INTERVAL)

        self.tasks: list = [
            self.heartbeat_task,
            self.screenshot_task,
            self.window_tracker,
            self.activity_state_task,
        ]

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)

    def _exit_gracefully(self, signum: int, frame) -> None:
        """Signal handler that sets the kill flag for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.kill_now = True

    def run(self) -> None:
        logger.info("Starting tracker")

        # Abort early if the platform isn't supported
        if tracker_settings.system not in self.SUPPORTED_SYSTEMS:
            logger.error(f"Unsupported system: {tracker_settings.system}")
            return

        try:
            while not self.kill_now:
                now = time.time()
                for t in self.tasks:
                    t.tick(now)
                time.sleep(0.1)  # Prevent high CPU usage

        finally:
            EventStore.log_activity(ActivityEventType.SHUTDOWN.value)
            EventStore.find_and_complete_incomplete_window_events()
            logger.info("Stopping tracker gracefully")
