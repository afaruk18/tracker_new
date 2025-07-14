from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from tracker.db.event_store import EventStore

from .window_title_provider import WindowTitleProvider


@dataclass
class WindowTrackerTask:
    _last_title: str | None = None
    _window_start: float | None = None
    _current_window_event_id: int | None = None
    _initialized: bool = False
    interval: int = 0

    def tick(self, now: float) -> None:
        """
        Main tracking method that should be called periodically.

        Tracks window focus changes and creates incomplete window event logs
        immediately when windows are focused, then completes them when the
        window changes (if they meet the duration threshold).

        Args:
            now: Current time as UNIX timestamp (seconds since epoch)
        """
        # Handle crash recovery on first run
        if not self._initialized:
            self._handle_crash_recovery()
            self._initialized = True

        current_title = WindowTitleProvider.current_title()

        if self._has_window_changed(current_title):
            self._handle_window_change(current_title, now)

    def _handle_crash_recovery(self) -> None:
        """Complete any incomplete window events from previous runs using heartbeat data."""
        logger.debug("Checking for incomplete window events from previous runs")
        EventStore.find_and_complete_incomplete_window_events()

    def _has_window_changed(self, current_title: str) -> bool:
        """Check if the focused window has changed since last tick."""
        return current_title != self._last_title

    def _handle_window_change(self, new_title: str, now: float) -> None:
        """Handle when user switches to a different window."""
        self._complete_previous_window_if_needed(now)
        self._start_tracking_new_window(new_title, now)

    def _complete_previous_window_if_needed(self, now: float) -> None:
        """Complete the previous window event if it meets the duration threshold."""
        if self._should_complete_previous_window(now):
            duration = now - self._window_start
            start_timestamp = datetime.fromtimestamp(self._window_start)
            end_timestamp = datetime.fromtimestamp(now)

            logger.info(
                f"Window '{self._last_title}' met duration threshold | "
                f"Start: {start_timestamp.isoformat()} | "
                f"End: {end_timestamp.isoformat()} | "
                f"Duration: {duration:.1f}s (>= {self.interval}s threshold)"
            )

            if self._current_window_event_id is not None:
                EventStore.complete_window_event(self._current_window_event_id, end_timestamp)
                logger.info(f"Completed window event ID {self._current_window_event_id} for '{self._last_title}'")
        elif self._current_window_event_id is not None:
            # Window didn't meet threshold - complete it with start time (zero duration)
            start_timestamp = datetime.fromtimestamp(self._window_start)
            EventStore.complete_window_event(self._current_window_event_id, start_timestamp)
            logger.debug(f"Window '{self._last_title}' did not meet threshold, completed with zero duration")

    def _should_complete_previous_window(self, now: float) -> bool:
        """Check if the previous window should be completed with actual duration."""
        return self._last_title is not None and self._window_start is not None and now - self._window_start >= self.interval

    def _start_tracking_new_window(self, window_title: str, now: float) -> None:
        """Begin tracking a new window focus session."""
        self._last_title = window_title
        self._window_start = now

        # Create incomplete window event immediately
        start_timestamp = datetime.fromtimestamp(now)
        self._current_window_event_id = EventStore.create_incomplete_window_event(window_title, start_timestamp)

        logger.debug(f"Started tracking window: '{window_title}' (event ID: {self._current_window_event_id})")

    def shutdown(self, now: float) -> None:
        """Complete any ongoing window event when the tracker shuts down.

        Args:
            now: Current time as UNIX timestamp (seconds since epoch)
        """
        if self._current_window_event_id is not None and self._window_start is not None:
            end_timestamp = datetime.fromtimestamp(now)

            # Complete the current window event regardless of duration
            EventStore.complete_window_event(self._current_window_event_id, end_timestamp)

            duration = now - self._window_start
            logger.info(f"Shutdown: Completed window event for '{self._last_title}' | Duration: {duration:.1f}s (event ID: {self._current_window_event_id})")

            self._current_window_event_id = None
