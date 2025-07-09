from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel, select

from tracker.config.tracker_settings import tracker_settings
from tracker.db.connect import get_session
from tracker.tables.activity_table import ActivityEvent
from tracker.tables.heartbeat_table import HeartbeatEvent
from tracker.tables.window_event_table import WindowEvent
from tracker.tables.working_sessions_table import WorkingSession


class EventStore:
    """Thin wrapper around SQLModel session for writing events."""

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
        # Compare raw strings to avoid circular imports with *ActivityEventType*
        ACTIVE, INACTIVE, STARTED, SCREEN_LOCKED, SHUTDOWN = (
            "Active",
            "Inactive",
            "Started",
            "Screen Locked",
            "Shutdown",  # Currently not supported
        )

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
    def log_activity(label: str) -> None:
        """Write an ActivityEvent and print a human-readable log line."""
        ts = datetime.now()

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
    def heartbeat(status: str = "Alive") -> None:
        """Write a HeartbeatEvent row."""
        ts = datetime.now()
        EventStore._insert(
            HeartbeatEvent(
                username=tracker_settings.user,
                timestamp=ts,
                status=status,
            )
        )

    @staticmethod
    def log_window_event(window_title: str) -> None:
        """Write a WindowEvent row whenever the active window title changes."""
        ts = datetime.now()
        EventStore._insert(
            WindowEvent(
                username=tracker_settings.user,
                timestamp=ts,
                window_title=window_title,
            )
        )
