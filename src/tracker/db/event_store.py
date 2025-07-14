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
        - On **Screen Locked**: close the most recent open session.
        - On **Shutdown**: close the most recent open session.
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
        SHUTDOWN = ActivityEventType.SHUTDOWN.value

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
            elif label in {INACTIVE, SCREEN_LOCKED, SHUTDOWN}:
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

    @staticmethod
    def create_incomplete_window_event(window_title: str, start_time: datetime) -> int:
        """Create an incomplete window event with null end_time and duration.

        Returns the ID of the created event for later updates.

        Args:
            window_title: Title of the focused window
            start_time: When the window became focused

        Returns:
            The ID of the created WindowEvent record
        """
        with get_session() as session:
            window_event = WindowEvent(
                username=tracker_settings.user,
                timestamp=start_time,  # For backward compatibility
                window_title=window_title,
                duration=None,  # Will be calculated when completed
                start_time=start_time,
                end_time=None,  # Incomplete - to be filled later
            )
            session.add(window_event)
            session.commit()
            session.refresh(window_event)  # Get the generated ID
            return window_event.id

    @staticmethod
    def complete_window_event(event_id: int, end_time: datetime) -> None:
        """Complete a window event by setting end_time and calculating duration.

        Args:
            event_id: ID of the WindowEvent to complete
            end_time: When the window lost focus
        """
        with get_session() as session:
            window_event = session.get(WindowEvent, event_id)
            if window_event and window_event.end_time is None:
                window_event.end_time = end_time
                if window_event.start_time:
                    window_event.duration = (end_time - window_event.start_time).total_seconds()
                session.add(window_event)
                session.commit()

    @staticmethod
    def find_and_complete_incomplete_window_events() -> None:
        """Find incomplete window events and complete them using heartbeat data.

        This method handles crash recovery by finding window events with null end_time
        and using the last heartbeat after the start_time to determine the end_time.
        """
        with get_session() as session:
            # Find all incomplete window events for the current user
            incomplete_events = session.exec(
                select(WindowEvent)
                .where(
                    WindowEvent.username == tracker_settings.user,
                    WindowEvent.end_time.is_(None),
                )
                .order_by(WindowEvent.start_time.asc())
            ).all()

            for event in incomplete_events:
                if event.start_time:
                    # Find the last heartbeat after this window event started
                    last_heartbeat = session.exec(
                        select(HeartbeatEvent)
                        .where(
                            HeartbeatEvent.username == tracker_settings.user,
                            HeartbeatEvent.timestamp > event.start_time,
                        )
                        .order_by(HeartbeatEvent.timestamp.desc())
                    ).first()

                    if last_heartbeat:
                        # Use the last heartbeat timestamp as the end time
                        event.end_time = last_heartbeat.timestamp
                        event.duration = (last_heartbeat.timestamp - event.start_time).total_seconds()
                        session.add(event)
                    else:
                        # No heartbeat found after start_time, use start_time as end_time (zero duration)
                        event.end_time = event.start_time
                        event.duration = 0.0
                        session.add(event)

            session.commit()
