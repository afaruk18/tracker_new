import sys
import time
from datetime import datetime

from loguru import logger

from tracker.config.logger_config import setup_logging
from tracker.config.tracker_settings import tracker_settings
from tracker.core import ActivityStateTask, HeartbeatTask, ScreenshotTask, SignalHandler, WindowTrackerTask
from tracker.db.event_store import EventStore
from tracker.tables.activity_table import ActivityEventType


class ActivityTracker:
    """Main application class for the activity tracker."""

    SUPPORTED_SYSTEMS: set[str] = {"windows", "darwin", "linux"}

    def __init__(self) -> None:
        """Initialize the activity tracker with all tasks and signal handling."""
        # Configure logging first, before any other operations
        setup_logging()

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

        # Set up signal handler
        self.signal_handler = SignalHandler(event_store=self.event_store)
        self.signal_handler.register_cleanup(self._cleanup_tasks)

    def _cleanup_tasks(self) -> None:
        """Perform cleanup on all tasks during shutdown."""
        now = time.time()

        # Complete any active window events
        if hasattr(self.window_tracker, "shutdown"):
            logger.info("Completing any active window events...")
            self.window_tracker.shutdown(now)

        # Other tasks don't require explicit cleanup at the moment
        # but this method provides a place to add it if needed

    def run(self) -> None:
        """Start the activity tracker and run the main loop."""
        logger.info("Starting tracker")

        # Abort early if the platform isn't supported
        if tracker_settings.system not in self.SUPPORTED_SYSTEMS:
            logger.error(f"Unsupported system: {tracker_settings.system}")
            return

        # Clean up any incomplete window events from previous runs
        EventStore.find_and_complete_incomplete_window_events()

        # Log that the tracker has started
        EventStore.log_activity(ActivityEventType.STARTED.value)

        try:
            while True:
                now = time.time()
                for t in self.tasks:
                    t.tick(now)
                time.sleep(0.1)  # Prevent high CPU usage

        finally:
            if self.signal_handler.is_signal_received():
                logger.info("Stopping tracker gracefully due to signal")
            else:
                logger.info("Stopping tracker gracefully due to normal application exit")
                self._cleanup_tasks()
                EventStore.log_activity(ActivityEventType.NORMAL_SHUTDOWN.value, timestamp=datetime.now())
