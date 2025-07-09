from __future__ import annotations

import signal
import sys
import time
from enum import StrEnum

from loguru import logger

from tracker.config.tracker_settings import tracker_settings
from tracker.core import EventStore, IdleDetector, ScreenLockDetector, ScreenshotCapturer, WindowTitleProvider


class ActivityEventType(StrEnum):
    STARTED = "Started"
    STOPPED = "Stopped by user"
    SCREEN_LOCKED = "Screen Locked"
    SCREEN_UNLOCKED = "Screen Unlocked"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    UNSUPPORTED = "Unsupported system"
    SHUTDOWN = "Shutdown"


class ActivityTracker:
    """Tracks idle/lock state and captures screenshots, persisting everything to Postgres."""

    SUPPORTED_SYSTEMS: set[str] = {"windows", "darwin", "linux"}

    def __init__(self) -> None:
        self.screenshot_dir = tracker_settings.screenshot_dir
        self.event_store = EventStore()
        self.idle_detector = IdleDetector()
        self.lock_detector = ScreenLockDetector()
        self.window_provider = WindowTitleProvider()
        self.capturer = ScreenshotCapturer(self.screenshot_dir)

    #     # Register signal handlers for graceful shutdown (e.g. systemd SIGTERM)
    #     self._register_signal_handlers()

    # def _register_signal_handlers(self) -> None:
    #     """Install signal handlers to log a shutdown event before exit."""

    #     def _handler(signum: int, frame) -> None:  # noqa: D401, ANN001
    #         # Avoid recursion if multiple signals received
    #         try:
    #             self.event_store.log_activity(ActivityEventType.SHUTDOWN.value)
    #         finally:
    #             # Exit immediately so the process can terminate cleanly
    #             sys.exit(0)

    #     # SIGTERM is the standard termination signal on *nix sent during shutdown
    #     signal.signal(signal.SIGTERM, _handler)

    #     # Some systems send SIGHUP on shutdown; register it if available
    #     if hasattr(signal, "SIGHUP"):
    #         signal.signal(signal.SIGHUP, _handler)

    def _run_sync(self) -> None:
        """Main synchronous loop orchestrating all tracking operations."""
        logger.info("Starting activity tracker")

        # Abort early if the platform isn't supported
        if tracker_settings.system not in self.SUPPORTED_SYSTEMS:
            self.event_store.log_activity(ActivityEventType.UNSUPPORTED.value)
            logger.error(f"Unsupported system: {tracker_settings.system}")
            return

        prev_idle = prev_locked = False
        prev_window_title: str | None = None
        last_heartbeat = last_shot = 0.0

        # Log the initial start event
        self.event_store.log_activity(ActivityEventType.STARTED.value)

        try:
            while True:
                now_t = time.time()

                # Periodic / reactive tasks handled by helper methods
                last_heartbeat = self._log_heartbeat(now_t, last_heartbeat)
                last_shot = self._capture_screenshot(now_t, last_shot)
                prev_window_title = self._track_window_title(prev_window_title)
                prev_locked, prev_idle = self._handle_lock_and_idle(prev_locked, prev_idle)

        except KeyboardInterrupt:
            self.event_store.log_activity(ActivityEventType.STOPPED.value)

    def _log_heartbeat(self, now_t: float, last_heartbeat: float) -> float:
        """Write a heartbeat event if the interval has elapsed."""
        if now_t - last_heartbeat >= tracker_settings.HEARTBEAT_EVERY:
            self.event_store.heartbeat()
            logger.info("Heartbeat")
            return now_t
        return last_heartbeat

    def _capture_screenshot(self, now_t: float, last_shot: float) -> float:
        """Capture a screenshot on the configured interval."""
        if tracker_settings.SCREENSHOT_INTERVAL and now_t - last_shot >= tracker_settings.SCREENSHOT_INTERVAL:
            self.capturer.capture_all()
            logger.info("Screenshot")
            return now_t
        return last_shot

    def _track_window_title(self, prev_window_title: str | None) -> str | None:
        """Log a window event when the active window title changes."""
        current_title = self.window_provider.current_title()
        if current_title != prev_window_title:
            self.event_store.log_window_event(current_title)
            logger.info(f"Window title: {current_title}")
            return current_title
        return prev_window_title

    def _handle_lock_and_idle(self, prev_locked: bool, prev_idle: bool) -> tuple[bool, bool]:
        """Detect screen lock/unlock and user idleness, emitting the appropriate events."""
        locked = self.lock_detector.is_locked()

        # Handle lock/unlock transitions
        if locked and not prev_locked:
            self.event_store.log_activity(ActivityEventType.SCREEN_LOCKED.value)
            logger.info("Screen locked")
            prev_locked, prev_idle = True, False
        elif not locked and prev_locked:
            self.event_store.log_activity(ActivityEventType.SCREEN_UNLOCKED.value)
            logger.info("Screen unlocked")
            prev_locked = False
            self.event_store.log_activity(ActivityEventType.ACTIVE.value)
            logger.info("User is active")

        # Only check for idle when the screen is unlocked
        if not locked:
            idle_seconds = self.idle_detector.seconds_idle()
            is_idle = idle_seconds >= tracker_settings.IDLE_THRESHOLD

            if is_idle and not prev_idle:
                self.event_store.log_activity(ActivityEventType.INACTIVE.value)
                logger.info("User is idle")
                prev_idle = True
            elif not is_idle and prev_idle:
                self.event_store.log_activity(ActivityEventType.ACTIVE.value)
                logger.info("User is active")
                prev_idle = False

        return prev_locked, prev_idle

    def run(self) -> None:
        """Start the activity tracker using a synchronous loop. Async can be added later."""
        self._run_sync()
