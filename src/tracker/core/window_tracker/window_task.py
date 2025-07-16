from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from tracker.db.event_store import EventStore

from .window_title_provider import WindowTitleProvider


@dataclass
class WindowTrackerTask:
    """Tracks window title changes and records window events with duration thresholds."""

    _last_title: str | None = None
    _window_start: float | None = None
    _current_window_event_id: int | None = None
    _initialized: bool = False
    interval: float = 0.0

    def tick(self) -> None:
        """Main tracking loop - checks for window changes and handles events."""
        now = time.time()

        # Handle crash recovery on first run
        if not self._initialized:
            logger.info("Checking for incomplete window events from previous runs")
            EventStore.find_and_complete_incomplete_window_events()
            self._initialized = True

        current_title = WindowTitleProvider.current_title()

        if current_title != self._last_title:
            # Complete previous window if exists
            if self._current_window_event_id is not None and self._window_start is not None:
                end_timestamp = datetime.fromtimestamp(now)

                # Check if previous window met duration threshold
                if now - self._window_start >= self.interval:  # Currently 0, so else not executed.
                    duration = now - self._window_start
                    start_timestamp = datetime.fromtimestamp(self._window_start)
                    logger.info(f"Window '{self._last_title}' met threshold | Duration: {duration:.1f}s | Event ID: {self._current_window_event_id}")
                    EventStore.complete_window_event(self._current_window_event_id, end_timestamp)
                else:
                    # Complete with zero duration (start time)
                    start_timestamp = datetime.fromtimestamp(self._window_start)
                    EventStore.complete_window_event(self._current_window_event_id, start_timestamp)
                    logger.info(f"Window '{self._last_title}' did not meet threshold, completed with zero duration")

            # Start tracking new window
            self._last_title = current_title
            self._window_start = now
            start_timestamp = datetime.fromtimestamp(now)
            self._current_window_event_id = EventStore.create_incomplete_window_event(current_title, start_timestamp)

            logger.info(f"Started tracking window: '{current_title}' (event ID: {self._current_window_event_id})")

    def shutdown(self, now: float) -> None:
        """Complete any ongoing window event when the tracker shuts down."""
        if self._current_window_event_id is not None and self._window_start is not None:
            end_timestamp = datetime.fromtimestamp(now)
            EventStore.complete_window_event(self._current_window_event_id, end_timestamp)

            duration = now - self._window_start
            logger.info(f"Shutdown: Completed window event for '{self._last_title}' | Duration: {duration:.1f}s")
            self._current_window_event_id = None
