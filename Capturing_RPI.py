"""Raspberry Pi side: stream the raw camera over WebRTC (no YOLO).

Useful for checking the camera/link on its own. Uses the same signaling endpoint
as Server_RPI.py, so only one of the two can run at a time (port 8080).
"""

from arducam_capturing.camera import CameraSource
from arducam_capturing.webrtc_server import CameraTrack, run_server


def main() -> None:
    source = CameraSource()
    try:
        run_server(lambda: CameraTrack(source))
    finally:
        source.close()


if __name__ == "__main__":
    main()
