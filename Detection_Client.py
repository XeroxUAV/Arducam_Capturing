"""Laptop side: receive the Pi's WebRTC video in an OpenCV window.

The Pi exposes an HTTP signaling endpoint. This client creates an SDP offer,
POSTs it to ``/offer``, applies the answer, and then pulls decoded frames from
the incoming video track. Media travels over UDP (SRTP), not TCP.

Press q or ESC (or close the window) to quit.
"""

from __future__ import annotations

import argparse
import asyncio
import time

import aiohttp
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription

DEFAULT_URL = "http://10.189.32.248:8080/offer"  # <-- the Pi's IP
WINDOW = "Arducam (WebRTC)"


async def display(track, done: asyncio.Event) -> None:
    """Decode frames from the track and show them."""
    frames = 0
    started = time.monotonic()
    try:
        while not done.is_set():
            frame = await track.recv()
            img = frame.to_ndarray(format="bgr24")
            frames += 1

            cv2.imshow(WINDOW, img)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                done.set()
                break
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                done.set()
                break

            if frames % 30 == 0:
                fps = frames / (time.monotonic() - started)
                h, w = img.shape[:2]
                print(f"{fps:5.1f} fps  {w}x{h}", flush=True)
    except Exception as exc:  # ConnectionError, MediaStreamError, ...
        print(f"video stopped: {exc}", flush=True)
        done.set()


async def run(url: str) -> None:
    pc = RTCPeerConnection()
    done = asyncio.Event()

    @pc.on("track")
    def on_track(track) -> None:
        print(f"receiving {track.kind} track", flush=True)
        if track.kind == "video":
            asyncio.ensure_future(display(track, done))

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        print(f"connection: {pc.connectionState}", flush=True)
        if pc.connectionState in ("failed", "closed"):
            done.set()

    pc.addTransceiver("video", direction="recvonly")
    await pc.setLocalDescription(await pc.createOffer())

    payload = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise SystemExit(f"signaling failed ({resp.status}): {await resp.text()}")
            answer = await resp.json()

    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
    )
    print(f"connected: {url}  (q or ESC to quit)", flush=True)

    try:
        await done.wait()
    finally:
        await pc.close()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"signaling endpoint (default: {DEFAULT_URL})",
    )
    asyncio.run(run(parser.parse_args().url))


if __name__ == "__main__":
    main()
