from __future__ import annotations

import os
import signal
import sys
from contextlib import suppress
from datetime import datetime
from types import FrameType
from typing import Callable, List, Optional

from loguru import logger

# Your project -- swap in your actual import paths
from tracker.db.event_store import EventStore
from tracker.tables.activity_table import ActivityEventType

# Type alias for handler callbacks
CleanupFn = Callable[[], None]


class SignalHandler:
    """Install exit-related signal handlers and coordinate graceful shutdown."""

    #: Exit signals we *always* hook
    _BASE_SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]

    #: Windows-specific mapping (Ctrl-Break, log-off, shutdown)
    if os.name == "nt" and hasattr(signal, "SIGBREAK"):
        _BASE_SIGNALS.append(signal.SIGBREAK)  # type: ignore[arg-type]

    def __init__(self, event_store: Optional[EventStore] = None) -> None:
        self._event_store: EventStore = event_store or EventStore()
        self._cleanup_fns: List[CleanupFn] = []
        self.signal_received = False
        self._install_handlers()

    def register_cleanup(self, fn: CleanupFn) -> None:
        self._cleanup_fns.append(fn)

    def _install_handlers(self) -> None:
        for sig in self._BASE_SIGNALS:
            try:
                signal.signal(sig, self._handle_exit)  # type: ignore[arg-type]
            except (ValueError, OSError):  # not allowed in threads / rare OSes
                logger.warning("Could not hook signal %s", sig)

    def _handle_exit(self, signum: int, frame: Optional[FrameType]) -> None:  # noqa: ANN001
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} – starting graceful shutdown…")
        self.signal_received = True
        # Audit log with best-effort error suppression
        with suppress(Exception):
            self._event_store.log_activity(
                ActivityEventType.SYSTEM_SHUTDOWN.value + f" ({signal_name})" if signal_name != "SIGINT" else ActivityEventType.USER_INTERRUPT.value,
                timestamp=datetime.now(),
            )

        for fn in self._cleanup_fns:
            try:
                fn()
            except Exception:  # noqa: BLE001
                logger.exception("Cleanup function %s raised", fn)

        sys.exit(0)

    def is_signal_received(self) -> bool:
        return self.signal_received
