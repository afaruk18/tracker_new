from __future__ import annotations

# NEW IMPORTS
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import SimpleQueue
from typing import List, Optional, ClassVar

from tracker.config.tracker_settings import tracker_settings
from tracker.tables.activity_table import ActivityEventType


# ---------------------------------------------------------------------------
# In-memory event models
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BaseEvent:
    """Common attributes for all events."""

    username: str
    timestamp: datetime


@dataclass(slots=True)
class ActivityEvent(BaseEvent):
    event: str  # human-readable label


@dataclass(slots=True)
class HeartbeatEvent(BaseEvent):
    pass


@dataclass(slots=True)
class WindowEvent(BaseEvent):
    window_title: str
    duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass(slots=True)
class WorkingSession:
    """Lightweight representation of a working session."""

    username: str
    start_time: datetime
    end_time: Optional[datetime] = None
    end_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Queue-based event store
# ---------------------------------------------------------------------------
class EventStore:
    """Queue-backed replacement for the original Postgres EventStore.

    All events are pushed onto a global in-memory queue for downstream
    processing.  This avoids the need for a database while keeping the
    external API unchanged so the rest of the tracker codebase does not need
    modifications.
    """

    # Global, process-wide queue that downstream consumers can read from.
    EVENT_QUEUE: ClassVar[SimpleQueue] = SimpleQueue()

    # In-process caches for *heartbeat* and *working session* bookkeeping.  These
    # replace the previous SQL queries used by *_handle_working_session*.
    _heartbeat_events: ClassVar[List[HeartbeatEvent]] = []
    _working_sessions: ClassVar[List[WorkingSession]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _insert(event: BaseEvent) -> None:
        """Push *event* onto the queue and keep any local bookkeeping."""
        if isinstance(event, HeartbeatEvent):
            EventStore._heartbeat_events.append(event)
        EventStore.EVENT_QUEUE.put(event)

    # ------------------------------------------------------------------
    # Working-session bookkeeping (re-implemented without SQL)
    # ------------------------------------------------------------------
    @classmethod
    def _handle_working_session(cls, label: str, ts: datetime) -> None:
        """Create or update *WorkingSession* records based on activity events."""
        ACTIVE = ActivityEventType.ACTIVE.value
        INACTIVE = ActivityEventType.INACTIVE.value
        STARTED = ActivityEventType.STARTED.value
        SCREEN_LOCKED = ActivityEventType.SCREEN_LOCKED.value

        # Helper: get last open session for the current user (if any)
        def _get_open_session() -> Optional[WorkingSession]:
            for ws in reversed(cls._working_sessions):
                if ws.username == tracker_settings.user and ws.end_time is None:
                    return ws
            return None

        open_session = _get_open_session()

        if label == ACTIVE:
            if open_session is None:
                cls._working_sessions.append(
                    WorkingSession(username=tracker_settings.user, start_time=ts)
                )
        elif label in {INACTIVE, SCREEN_LOCKED}:
            if open_session is not None:
                open_session.end_time = ts
                open_session.end_reason = label
        elif label == STARTED:
            if open_session is not None:
                # Find the last heartbeat between *open_session.start_time* and *ts*
                last_hb_ts: Optional[datetime] = None
                for hb in reversed(cls._heartbeat_events):
                    if (
                        hb.username == tracker_settings.user
                        and open_session.start_time < hb.timestamp < ts
                    ):
                        last_hb_ts = hb.timestamp
                        break
                end_ts = last_hb_ts or ts
                open_session.end_time = end_ts
                open_session.end_reason = label

    # ------------------------------------------------------------------
    # Public API (unchanged signature)
    # ------------------------------------------------------------------
    @staticmethod
    def log_activity(label: str, timestamp: datetime | None = None) -> None:
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
        ts = timestamp or datetime.now()
        hb = HeartbeatEvent(username=tracker_settings.user, timestamp=ts)
        EventStore._insert(hb)

    @staticmethod
    def log_window_event(
        window_title: str,
        timestamp: datetime | None = None,
        duration: float = 0.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> None:
        # Determine the actual start and end times to use – keep compatibility with
        # the old signature that accepted either (timestamp + duration) *or*
        # (start_time + end_time).
        if start_time is not None and end_time is not None:
            actual_start_time = start_time
            actual_end_time = end_time
            actual_duration = (end_time - start_time).total_seconds()
            ts = start_time
        else:
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
