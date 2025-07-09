from __future__ import annotations

import asyncio
import os
import subprocess
import time
from datetime import datetime

import mss
from PIL import Image

from tracker.config.tracker_settings import tracker_settings
from tracker.db.connect import get_session
from tracker.tables.activity_table import ActivityEvent
from tracker.tables.heartbeat_table import HeartbeatEvent


class ActivityTracker:
    """Tracks idle/lock state and captures screenshots, persisting everything to Postgres."""

    def __init__(self) -> None:
        self.screenshot_dir = tracker_settings.screenshot_dir

    def _insert_event_row(self, row: ActivityEvent) -> None:
        with get_session() as session:
            session.add(row)
            session.commit()

    @staticmethod
    def _get_idle_time() -> float:
        try:
            #! TODO: Windows support
            return int(subprocess.check_output(["xprintidle"])) / 1000.0
        except Exception:
            return 0.0

    @staticmethod
    def _get_current_session_id() -> str | None:
        try:
            uid = os.getuid()
            res = subprocess.run(
                ["loginctl", "list-sessions", "--no-legend"],
                capture_output=True,
                check=False,
            )
            for line in res.stdout.decode().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[2] == str(uid):
                    return parts[0]
        except Exception:
            pass
        return None

    @staticmethod
    def _is_screen_locked() -> bool:
        try:
            system = tracker_settings.system
            if system == "Windows":
                import ctypes

                user32 = ctypes.windll.User32
                hDesktop = user32.OpenDesktopW("Default", 0, False, 0x100)
                if hDesktop:
                    locked = user32.SwitchDesktop(hDesktop) == 0
                    user32.CloseDesktop(hDesktop)
                    return locked
                return False
            elif system == "Linux":
                try:
                    res = subprocess.run(
                        ["gnome-screensaver-command", "-q"],
                        capture_output=True,
                        check=False,
                    )
                    if b"is active" in res.stdout:
                        return True
                except Exception:
                    pass
                # Try loginctl as fallback
                try:
                    res = subprocess.run(
                        ["loginctl", "show-session", str(ActivityTracker._get_current_session_id()), "-p", "LockedHint"],
                        capture_output=True,
                        check=False,
                    )
                    if b"LockedHint=yes" in res.stdout:
                        return True
                except Exception:
                    pass
                return False
            else:
                # Other platforms not supported
                return False
        except Exception:
            return False

    @staticmethod
    def _get_focused_window_title() -> str:
        try:
            win_id = subprocess.check_output(["xdotool", "getwindowfocus"]).strip()
            title = subprocess.check_output(["xdotool", "getwindowname", win_id]).decode().strip()
            return title
        except Exception:
            return "N/A"

    def _log(self, event: str, window: str = "") -> None:
        ts = datetime.now()
        ts_txt = ts.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts_txt}] {event}" + (f" | {window}" if window else ""))

        row = ActivityEvent(
            username=tracker_settings.user,
            timestamp=ts,
            event=event,
            window_title=window,
        )
        self._insert_event_row(row)

    def _capture_screens(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with mss.mss() as sct:
            for i, mon in enumerate(sct.monitors[1:], 1):  # skip the "all" monitor 0
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.rgb)

                fname = self.screenshot_dir / f"monitor{i}_{stamp}.{tracker_settings.IMAGE_FORMAT}"

                if tracker_settings.IMAGE_FORMAT.lower() == "jpeg":
                    img.save(fname, quality=tracker_settings.IMAGE_QUALITY)
                else:
                    img.save(fname)

    def _run_sync(self) -> None:
        prev_idle = prev_locked = False
        last_heartbeat = last_shot = 0.0

        current_window = self._get_focused_window_title()
        self._log("Started", current_window)

        try:
            while True:
                now_t = time.time()

                # Heartbeat
                if now_t - last_heartbeat >= tracker_settings.HEARTBEAT_EVERY:
                    now_ts = datetime.now()
                    row = HeartbeatEvent(
                        username=tracker_settings.user,
                        timestamp=now_ts,
                        status="Alive",
                    )
                    self._insert_event_row(row)

                    last_heartbeat = now_t

                # Screenshots
                if tracker_settings.SCREENSHOT_INTERVAL and now_t - last_shot >= tracker_settings.SCREENSHOT_INTERVAL:
                    self._capture_screens()
                    last_shot = now_t

                # Screen‑lock handling
                locked = self._is_screen_locked()
                current_window = self._get_focused_window_title()

                if locked and not prev_locked:
                    self._log("Screen Locked", current_window)
                    prev_locked, prev_idle = True, False
                elif not locked and prev_locked:
                    self._log("Screen Unlocked", current_window)
                    prev_locked = False
                    self._log("Active", current_window)

                # Idle detection when unlocked
                if not locked:
                    idle_seconds = self._get_idle_time()
                    is_idle = idle_seconds >= tracker_settings.IDLE_THRESHOLD

                    if is_idle and not prev_idle:
                        self._log("Inactive", current_window)
                        prev_idle = True
                    elif not is_idle and prev_idle:
                        self._log("Active", current_window)
                        prev_idle = False

                time.sleep(1)

        except KeyboardInterrupt:
            self._log("Stopped by user")

    # ------------------------------------------------------------------
    # Async implementation
    # ------------------------------------------------------------------

    async def _db_add_row(self, row: ActivityEvent | HeartbeatEvent) -> None:  # type: ignore[arg-type]
        """Insert a SQLModel row in a background thread so we don't block the event loop."""
        await asyncio.to_thread(self._insert_event_row, row)  # type: ignore[arg-type]

    async def _heartbeat_loop(self) -> None:
        """Continuously write heartbeat signals at the configured interval."""
        while True:
            now_ts = datetime.now()

            # Persist to database
            row = HeartbeatEvent(
                username=tracker_settings.user,
                timestamp=now_ts,
                status="Alive",
            )
            await self._db_add_row(row)

            await asyncio.sleep(tracker_settings.HEARTBEAT_EVERY)

    async def _activity_loop(self) -> None:
        """Monitor screen state, idle/active events, and screenshots."""
        prev_idle = prev_locked = False
        last_shot = 0.0

        current_window = await asyncio.to_thread(self._get_focused_window_title)
        await asyncio.to_thread(self._log, "Started", current_window)

        while True:
            now_t = time.time()

            # Screenshots -------------------------------------------------
            if tracker_settings.SCREENSHOT_INTERVAL and now_t - last_shot >= tracker_settings.SCREENSHOT_INTERVAL:
                await asyncio.to_thread(self._capture_screens)
                last_shot = now_t

            # Screen-lock and idle detection -----------------------------
            locked = await asyncio.to_thread(self._is_screen_locked)
            current_window = await asyncio.to_thread(self._get_focused_window_title)

            if locked and not prev_locked:
                await asyncio.to_thread(self._log, "Screen Locked", current_window)
                prev_locked, prev_idle = True, False
            elif not locked and prev_locked:
                await asyncio.to_thread(self._log, "Screen Unlocked", current_window)
                prev_locked = False
                await asyncio.to_thread(self._log, "Active", current_window)

            if not locked:
                idle_seconds = await asyncio.to_thread(self._get_idle_time)
                is_idle = idle_seconds >= tracker_settings.IDLE_THRESHOLD

                if is_idle and not prev_idle:
                    await asyncio.to_thread(self._log, "Inactive", current_window)
                    prev_idle = True
                elif not is_idle and prev_idle:
                    await asyncio.to_thread(self._log, "Active", current_window)
                    prev_idle = False

            await asyncio.sleep(1)

    async def _async_main(self) -> None:
        """Run heartbeat and activity loops concurrently."""
        await asyncio.gather(
            self._heartbeat_loop(),
            self._activity_loop(),
        )

    # Public entry-point -----------------------------------------------

    def run(self) -> None:
        """Launch the tracker using asyncio."""
        asyncio.run(self._async_main())
