import cv2, socket, struct, time, traceback

def open_camera(max_index=10):
    """Return the first /dev/videoN node that can actually stream frames.

    The Arducam UVC camera exposes two nodes: a capture node and a metadata
    node.  The metadata node cannot be opened by OpenCV, and indices are not
    stable across reboots, so don't hardcode one.
    """
    for index in range(max_index):
        c = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if c.isOpened() and c.read()[0]:
            print(f"using /dev/video{index}", flush=True)
            return c
        c.release()
    raise RuntimeError("no usable V4L2 capture device found")


# Output size sent to the laptop. The Arducam B0495 only exposes 1920x1200
# and 960x600 natively, so capture at 960x600 and downscale to 640x480.
OUT_W, OUT_H = 640, 480

cap = open_camera()
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
print("opened:", cap.isOpened(), flush=True)
print(f"capture: {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x"
      f"{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} -> {OUT_W}x{OUT_H}", flush=True)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 8080)); s.listen(1)
print("Waiting for laptop connection...", flush=True)
c, a = s.accept()
c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
print(f"Connected: {a}", flush=True)

try:
    n = 0
    while True:
        print(f"[{n}] calling cap.read()...", flush=True)
        ret, frame = cap.read()
        frame = cv2.rotate(frame, cv2.ROTATE_180) 
        print(f"[{n}] cap.read() returned ret={ret}", flush=True)
        if not ret:
            print(f"[{n}] !! read failed, breaking", flush=True)
            break
        if frame.shape[1] != OUT_W or frame.shape[0] != OUT_H:
            frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(f"[{n}] encode ok={ok} size={len(buf) if ok else 0}", flush=True)
        if not ok:
            continue
        data = buf.tobytes()
        c.sendall(struct.pack(">L", len(data)) + data)
        print(f"[{n}] sent {len(data)} bytes", flush=True)
        n += 1
except ConnectionError:
    print("client disconnected", flush=True)
except Exception:
    traceback.print_exc()
finally:
    print("finally: closing", flush=True)
    cap.release(); c.close(); s.close()