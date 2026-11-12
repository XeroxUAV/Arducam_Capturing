"""Raspberry Pi side: capture, run YOLO, stream annotated video over WebRTC.

The laptop connects from Detection_Client.py. Signaling happens on
http://<pi-ip>:8080/offer, video flows over UDP via WebRTC (SRTP).
"""

from arducam_capturing.camera import CameraSource
from arducam_capturing.detection import DEFAULT_MODEL, make_annotator
from arducam_capturing.webrtc_server import CameraTrack, run_server

# Model shipped in the repo; override if you use a different checkpoint.
MODEL_PATH = DEFAULT_MODEL


def main() -> None:
    annotate = make_annotator(MODEL_PATH)
    source = CameraSource()
    try:
        run_server(lambda: CameraTrack(source, annotate))
    finally:
        source.close()


if __name__ == "__main__":
    main()
