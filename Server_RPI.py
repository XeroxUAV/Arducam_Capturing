import cv2, socket, struct, time, traceback

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
print("opened:", cap.isOpened(), flush=True)

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
        print(f"[{n}] cap.read() returned ret={ret}", flush=True)
        if not ret:
            print(f"[{n}] !! read failed, breaking", flush=True)
            break
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(f"[{n}] encode ok={ok} size={len(buf) if ok else 0}", flush=True)
        if not ok:
            continue
        data = buf.tobytes()
        c.sendall(struct.pack(">L", len(data)) + data)
        print(f"[{n}] sent {len(data)} bytes", flush=True)
        n += 1
except Exception:
    traceback.print_exc()
finally:
    print("finally: closing", flush=True)
    cap.release(); c.close(); s.close()