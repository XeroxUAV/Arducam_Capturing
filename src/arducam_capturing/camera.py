"""Shared V4L2 camera access for the WebRTC servers.

The Arducam B0495 is a UVC camera: it exposes a capture node *and* a metadata
node, and the numbering is not stable across reboots. ``open_camera`` picks the
first node that can actually deliver a frame.

A camera can only be opened once, so every WebRTC track shares a single
``CameraSource`` which reads in a background thread. Consumers always get the
newest frame, so a slow consumer (YOLO inference) skips frames instead of
falling behind.
"""

from __future__ import annotations

import threading
import time

import cv2

# Native mode used for capture; frames are downscaled to 640x480 for streaming.
CAPTURE_W, CAPTURE_H = 960, 600


def open_camera(max_index: int = 10) -> cv2.VideoCapture:
    """Open the first /dev/videoN node that can actually stream frames."""
    for index in range(max_index):
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap.release()
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
        ok, _ = cap.read()
        if ok:
            print(
                f"using /dev/video{index} at "
                f"{cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x"
                f"{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}",
                flush=True,
            )
            return cap
        cap.release()
    raise RuntimeError("no usable V4L2 capture device found")


class CameraSource:
    """Continuously reads frames and hands out the newest one."""

    def __init__(self, max_index: int = 10, rotate_180: bool = True) -> None:
        self.cap = open_camera(max_index)
        self._rotate_180 = rotate_180
        self._condition = threading.Condition()
        self._frame = None
        self._seq = 0
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.005)
                continue
            if self._rotate_180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            with self._condition:
                self._frame = frame
                self._seq += 1
                self._condition.notify_all()

    def next_frame(self, after_seq: int = 0, timeout: float = 5.0):
        """Block until a frame newer than ``after_seq`` exists.

        Returns ``(frame, seq)``, or ``(None, after_seq)`` on timeout.
        """
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._seq <= after_seq:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, after_seq
                self._condition.wait(remaining)
            return self._frame.copy(), self._seq

    def close(self) -> None:
        self._running = False
        with self._condition:
            self._condition.notify_all()
        self._thread.join(timeout=1.0)
        self.cap.release()
