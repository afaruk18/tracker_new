from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import SQLModel, select

from tracker.config.tracker_settings import tracker_settings
from tracker.db.connect import get_session
from tracker.tables.activity_table import ActivityEvent, ActivityEventType
from tracker.tables.heartbeat_table import HeartbeatEvent
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
        with get_session() as session:
            session.add(row)
            session.commit()

    @staticmethod
    def _handle_working_session(label: str, ts: datetime) -> None:
        """Create or update *WorkingSession* rows based on activity events.

        Rules:
        - On **Active**: start a new session unless one is already open.
        - On **Inactive**: close the most recent open session.
        - On **Started**: close any lingering open session from the previous run
          using the timestamp of the last heartbeat between the *Active* and
          the *Started* events (or *ts* itself if no heartbeat exists).
        """
        # Work with *str* values to avoid mixing *str* and *StrEnum* during
        # downstream comparisons.  Using the ``.value`` attribute keeps the
        # behaviour identical to the original implementation that relied on
        # raw strings only.

        ACTIVE = ActivityEventType.ACTIVE.value
        INACTIVE = ActivityEventType.INACTIVE.value
        STARTED = ActivityEventType.STARTED.value
        SCREEN_LOCKED = ActivityEventType.SCREEN_LOCKED.value

        with get_session() as session:
            # The most recent open session (if any)
            open_session = session.exec(
                select(WorkingSession)
                .where(
                    WorkingSession.username == tracker_settings.user,
                    WorkingSession.end_time.is_(None),
                )
                .order_by(WorkingSession.start_time.desc())
            ).first()

            if label == ACTIVE:
                if open_session is None:
                    session.add(
                        WorkingSession(
                            username=tracker_settings.user,
                            start_time=ts,
                        )
                    )
            elif label in {INACTIVE, SCREEN_LOCKED}:
                if open_session is not None:
                    open_session.end_time = ts
                    open_session.end_reason = label
                    session.add(open_session)
            elif label == STARTED:
                if open_session is not None:
                    # Find the last heartbeat between *open_session.start_time* and *ts*
                    last_hb = session.exec(
                        select(HeartbeatEvent)
                        .where(
                            HeartbeatEvent.username == tracker_settings.user,
                            HeartbeatEvent.timestamp > open_session.start_time,
                            HeartbeatEvent.timestamp < ts,
                        )
                        .order_by(HeartbeatEvent.timestamp.desc())
                    ).first()
                    end_ts = last_hb.timestamp if last_hb else ts
                    open_session.end_time = end_ts
                    open_session.end_reason = label
                    session.add(open_session)
            # Commit any pending changes (if we made modifications)
            session.commit()

    @staticmethod
    def log_activity(label: str, timestamp: datetime | None = None) -> None:
        """Write an ActivityEvent and print a human-readable log line.

        The optional *timestamp* argument allows callers to record a specific
        time rather than the moment this function is invoked. If *timestamp*
        is *None*, the current time (``datetime.now()``) is used for backward
        compatibility.
        """
        ts = timestamp or datetime.now()

        EventStore._insert(
            ActivityEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event=label,
            )
        )

        # Update working-session state once the activity row is recorded
        EventStore._handle_working_session(label, ts)

    @staticmethod
    def heartbeat(timestamp: datetime | None = None) -> None:
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
