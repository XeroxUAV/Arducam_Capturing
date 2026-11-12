# Arducam_Capturing

Capture video from a USB Arducam (B0495) on a Raspberry Pi, optionally run YOLO
detection on the Pi, and stream the result to a laptop over **WebRTC**.

## How it works

```
Pi                                         Laptop
┌──────────────────────────┐   HTTP POST  ┌────────────────────┐
│ Server_RPI.py            │  /offer SDP  │ Detection_Client.py│
│  CameraSource (V4L2)     │ <──────────> │  aiortc            │
│  YOLO annotation         │              │  OpenCV window     │
│  aiortc CameraTrack      │ ═══ UDP ═══> │                    │
└──────────────────────────┘  SRTP video  └────────────────────┘
```

Only the SDP handshake uses TCP/HTTP. Video itself is sent peer-to-peer over
UDP via WebRTC (SRTP), so there is no frame-length protocol to get wrong and
no head-of-line blocking on retransmits.

## Setup (Raspberry Pi OS)

`libcamera` and `picamera2` are **not** available on PyPI — they are shipped as
compiled Debian packages for the system Python only. The venv must therefore be
built from the system interpreter with access to system site-packages.

```bash
# 1. System packages (once)
sudo apt install python3-libcamera python3-picamera2 python3-venv

# 2. Venv based on the system Python, with system packages visible
rm -rf .venv
uv venv --python /usr/bin/python3 --system-site-packages

# 3. Project dependencies (aiortc, aiohttp, opencv, ultralytics)
uv sync

# 4. Verify
uv run python -c "import aiortc, aiohttp, cv2; print('WebRTC stack OK')"
```

If you ever see `ModuleNotFoundError: No module named 'libcamera'`, the venv was
created without `--system-site-packages`; recreate it with the commands above.

Run everything with the venv interpreter (`uv run python ...` or
`source .venv/bin/activate`). The system `python` does not have these packages.

## Run on the Pi

```bash
# Annotated stream (YOLO + boxes)
uv run python Server_RPI.py

# or the raw camera, no detection
uv run python Capturing_RPI.py
```

Both listen on `0.0.0.0:8080` and print the chosen camera node, e.g.
`using /dev/video0 at 960x600`. Only one can run at a time (same port).

## Run on the laptop

```bash
uv run python Detection_Client.py http://<pi-ip>:8080/offer
```

The default URL lives at the top of `Detection_Client.py`. Press **q** or
**ESC** (or close the window) to stop; the console prints fps and frame size.

## Networking notes

- WebRTC allocates UDP ports dynamically (typically 49152–65535). Both hosts
  must be able to reach each other on UDP; on a flat LAN nothing needs
  configuring, but a firewall must allow those ports.
- `Detection_Client.py` uses host candidates only (no STUN/TURN), which is
  enough on the same LAN. Across NAT you would need to add an `iceServers`
  entry to the `RTCPeerConnection` in both scripts.
- Resolution: the B0495 only exposes 1920x1200 and 960x600 natively, so the Pi
  captures at 960x600 and scales to **640x480** before encoding.
- The camera is opened once and shared by every connection; frames are pulled
  from a background capture thread, so slow inference drops frames instead of
  queueing latency.

## Files

| Path | Purpose |
| --- | --- |
| `Server_RPI.py` | Pi: YOLO-annotated WebRTC server |
| `Capturing_RPI.py` | Pi: raw WebRTC server |
| `Detection_Client.py` | Laptop: WebRTC client + OpenCV window |
| `src/arducam_capturing/camera.py` | V4L2 discovery + threaded camera source |
| `src/arducam_capturing/detection.py` | YOLO loading and box drawing |
| `src/arducam_capturing/webrtc_server.py` | Signaling endpoint + `CameraTrack` |
