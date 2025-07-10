from __future__ import annotations

from dataclasses import dataclass

from .screenshot_capturer import ScreenshotCapturer


@dataclass
class ScreenshotTask:
    """
    Periodically triggers screenshot capture at a specified interval.

    This class manages the timing and execution of screenshot captures using a provided
    ScreenshotCapturer instance. It tracks the last time a screenshot was taken and ensures
    that screenshots are only captured when the configured interval has elapsed.

    Attributes:
        interval (int): The minimum number of seconds between consecutive screenshot captures.
        capturer (ScreenshotCapturer): The object responsible for performing the screenshot capture.
        _last (float | None): The UNIX timestamp of the last screenshot capture, or None if no capture has occurred yet.

    Methods:
        tick(now: float) -> None:
            Checks if the interval has elapsed since the last screenshot. If so, triggers
            the capturer to take screenshots and updates the last capture timestamp.

            Args:
                now (float): The current time as a UNIX timestamp (seconds since epoch).

            Behavior:
                - On the first invocation (when _last is None), captures screenshots immediately.
                - On subsequent invocations, captures screenshots only if at least `interval` seconds
                  have passed since the last capture.

            Side Effects:
                - Updates the internal _last timestamp to the current time if a screenshot is captured.
                - Calls capturer.capture_all_monitors() to perform the screenshot operation.
    """

    interval: int
    capturer: ScreenshotCapturer
    _last: float | None = None

    def tick(self, now: float) -> None:
        """
        Trigger a screenshot capture if the configured interval has elapsed.

        Args:
            now (float): The current time as a UNIX timestamp (seconds since epoch).

        This method should be called periodically (e.g., in a main loop). It checks whether
        the specified interval has passed since the last screenshot was captured. If so, or if
        this is the first invocation (i.e., no previous screenshot has been captured), it calls
        the capturer's capture_all_monitors() method and updates the internal timestamp.
        """
        if self._last is None or now - self._last >= self.interval:
            self._last = now
            self.capturer.capture_all_monitors()
