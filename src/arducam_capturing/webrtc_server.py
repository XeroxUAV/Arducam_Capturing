"""WebRTC video streaming over a tiny HTTP signaling endpoint.

The Pi is the answerer: the laptop POSTs an SDP offer to ``/offer`` and gets an
SDP answer back. Media then flows peer-to-peer over UDP (SRTP), so the TCP
frame protocol is gone.

Only the signaling endpoint is HTTP; nothing carries video over TCP anymore.
"""

from __future__ import annotations

import asyncio
import fractions
import logging
from typing import Callable

import av
import cv2
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiohttp import web

from .camera import CameraSource

log = logging.getLogger("arducam.webrtc")

# Size sent to the laptop.
OUT_W, OUT_H = 640, 480
FPS = 30

# Called with a BGR frame; returns a new annotated BGR frame.
Annotate = Callable[[object], "object"]


class CameraTrack(MediaStreamTrack):
    """A video track fed by a shared CameraSource."""

    kind = "video"

    def __init__(
        self,
        source: CameraSource,
        annotate: Annotate | None = None,
        fps: int = FPS,
    ) -> None:
        super().__init__()
        self._source = source
        self._annotate = annotate
        self._seq = 0
        self._pts = 0
        self._step = 90000 // fps

    async def recv(self) -> av.VideoFrame:
        frame, seq = await asyncio.to_thread(self._source.next_frame, self._seq)
        if frame is None:
            raise RuntimeError("camera stopped delivering frames")
        self._seq = seq

        if frame.shape[1] != OUT_W or frame.shape[0] != OUT_H:
            frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)

        if self._annotate is not None:
            frame = await asyncio.to_thread(self._annotate, frame)

        video = av.VideoFrame.from_ndarray(frame, format="bgr24")
        video.pts = self._pts
        video.time_base = fractions.Fraction(1, 90000)
        self._pts += self._step
        return video


def create_app(track_factory: Callable[[], MediaStreamTrack]) -> web.Application:
    pcs: set[RTCPeerConnection] = set()

    async def index(request: web.Request) -> web.Response:
        return web.json_response(
            {"status": "ok", "endpoint": "/offer", "video": f"{OUT_W}x{OUT_H}@{FPS}"}
        )

    async def offer(request: web.Request) -> web.Response:
        params = await request.json()
        if "sdp" not in params or "type" not in params:
            raise web.HTTPBadRequest(text="expected {'sdp': ..., 'type': ...}")

        pc = RTCPeerConnection()
        pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            log.info("connection state: %s", pc.connectionState)
            if pc.connectionState in ("failed", "closed", "disconnected"):
                await pc.close()
                pcs.discard(pc)

        track = track_factory()
        pc.addTrack(track)

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        )
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.json_response(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        )

    async def on_shutdown(app: web.Application) -> None:
        await asyncio.gather(*(pc.close() for pc in list(pcs)))
        pcs.clear()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)
    return app


def run_server(
    track_factory: Callable[[], MediaStreamTrack],
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log.info("signaling on http://%s:%d (POST /offer)", host, port)
    log.info("waiting for a client...")
    web.run_app(create_app(track_factory), host=host, port=port, print=None)
