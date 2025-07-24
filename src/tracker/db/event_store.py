from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import SQLModel

from tracker.config.tracker_settings import tracker_settings
from tracker.event_queue import enqueue
from tracker.tables.activity_table import ActivityEvent, ActivityEventType
from tracker.tables.heartbeat_table import HeartbeatEvent, HeartbeatType
from tracker.tables.window_event_table import WindowEvent
from tracker.tables.working_sessions_table import WorkingSession


class EventStore:
    """Database event storage interface for the tracker system.

    The EventStore class provides a high-level API for recording various types of
    tracking events to the database. It serves as the primary interface between
    the tracking components and the underlying database storage, handling session
    management and data persistence automatically.

    This class manages four main types of events:
    - Activity events (active/inactive/started/screen_locked states)
    - Heartbeat events (periodic status updates)
    - Window events (active window title changes)
    - Working session tracking (automatically derived from activity events)

    """

    @staticmethod
    def _insert(row: SQLModel) -> None:
        enqueue(row)

    _current_session: WorkingSession | None = None
    _incomplete_window_events: dict[int, WindowEvent] = {}
    _window_event_id: int = 1

    @classmethod
    def _handle_working_session(cls, label: ActivityEventType, ts: datetime) -> None:
        if label == ActivityEventType.ACTIVE:
            if cls._current_session is None:
                cls._current_session = WorkingSession(
                    username=tracker_settings.user,
                    start_time=ts,
                )
        elif label in {
            ActivityEventType.INACTIVE,
            ActivityEventType.SCREEN_LOCKED,
            ActivityEventType.NORMAL_SHUTDOWN,
            ActivityEventType.SYSTEM_SHUTDOWN,
            ActivityEventType.USER_INTERRUPT,
        }:
            if cls._current_session is not None:
                cls._current_session.end_time = ts
                cls._current_session.end_reason = label
                enqueue(cls._current_session)
                cls._current_session = None

    @staticmethod
    def log_event(label: ActivityEventType) -> None:
        """Write an ActivityEvent and print a human-readable log line.

        The optional *timestamp* argument allows callers to record a specific
        time rather than the moment this function is invoked. If *timestamp*
        is *None*, the current time (``datetime.now()``) is used for backward
        compatibility.
        """
        ts = datetime.now()

        EventStore._insert(
            ActivityEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event=label.value,
            )
        )

        EventStore._handle_working_session(label, ts)

    @staticmethod
    def heartbeat(timestamp: datetime | None = None, type: HeartbeatType = HeartbeatType.REGULAR) -> None:
        """Write a HeartbeatEvent row.

        The optional *timestamp* argument allows callers to record a specific
        time rather than the moment this function is invoked. If *timestamp*
        is *None*, the current time (``datetime.now()``) is used for backward
        compatibility.
        """
        ts = timestamp or datetime.now()
        EventStore._insert(
            HeartbeatEvent(
                username=tracker_settings.user,
                timestamp=ts,
                type=type,
            )
        )

    @staticmethod
    def log_window_event(window_title: str, timestamp: datetime | None = None, duration: float = 0.0, start_time: datetime | None = None, end_time: datetime | None = None) -> None:
        """Write a *WindowEvent* row.

        The method supports two ways of specifying timing information:
        1. Legacy: timestamp (start time) + duration
        2. New: start_time + end_time (duration calculated automatically)

        If start_time and end_time are provided, they take precedence and duration
        is calculated from them. Otherwise, falls back to timestamp + duration.

        Args:
            window_title: Title of the focused window
            timestamp: Legacy start time (for backward compatibility)
            duration: Legacy duration in seconds (for backward compatibility)
            start_time: Explicit start timestamp of window focus
            end_time: Explicit end timestamp of window focus
        """
        # Determine the actual start and end times to use
        if start_time is not None and end_time is not None:
            actual_start_time = start_time
            actual_end_time = end_time
            actual_duration = (end_time - start_time).total_seconds()
            # Use start_time for timestamp field for consistency
            ts = start_time
        else:
            # Fall back to legacy parameters
            ts = timestamp or datetime.now()
            actual_start_time = ts
            actual_end_time = ts + timedelta(seconds=duration) if duration > 0 else None
            actual_duration = duration

        EventStore._insert(
            WindowEvent(
                username=tracker_settings.user,
                timestamp=ts,
                window_title=window_title,
                duration=actual_duration,
                start_time=actual_start_time,
                end_time=actual_end_time,
            )
        )

    @staticmethod
    def create_incomplete_window_event(window_title: str, start_time: datetime) -> int:
        """Create an incomplete window event and store it in memory."""
        event_id = EventStore._window_event_id
        EventStore._window_event_id += 1
        window_event = WindowEvent(
            id=event_id,
            username=tracker_settings.user,
            window_title=window_title,
            duration=None,
            start_time=start_time,
            end_time=None,
        )
        EventStore._incomplete_window_events[event_id] = window_event
        return event_id

    @staticmethod
    def complete_window_event(event_id: int, end_time: datetime) -> None:
        """Complete a stored window event and enqueue it."""
        window_event = EventStore._incomplete_window_events.pop(event_id, None)
        if window_event and window_event.end_time is None:
            window_event.end_time = end_time
            if window_event.start_time:
                window_event.duration = (
                    window_event.end_time - window_event.start_time
                ).total_seconds()
            enqueue(window_event)

    @staticmethod
    def find_and_complete_incomplete_window_events() -> None:
        """Complete any window events that never received an end time."""
        for event_id, event in list(EventStore._incomplete_window_events.items()):
            if event.start_time and event.end_time is None:
                event.end_time = event.start_time
                event.duration = 0.0
                enqueue(event)
                EventStore._incomplete_window_events.pop(event_id, None)
