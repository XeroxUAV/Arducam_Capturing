import socket
import struct

import cv2
import numpy as np
from ultralytics import YOLO

SERVER_IP = '10.189.32.248'
SERVER_PORT = 8080

MODEL_PATH = 'best.pt'
CONF_THRES = 0.4
# Set to a class id to draw only that class, or None for all classes
WINDOW_CLASS_ID = None


def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed by server")
        buf += chunk
    return buf


def draw_detections(frame, results):
    """Draw bounding boxes + labels for one frame in place."""
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return 0

    xyxy = boxes.xyxy.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()
    clss = boxes.cls.cpu().numpy().astype(int)
    names = results[0].names

    drawn = 0
    for (x1, y1, x2, y2), conf, cls_id in zip(xyxy, confs, clss):
        if WINDOW_CLASS_ID is not None and cls_id != WINDOW_CLASS_ID:
            continue

        label = f"{names[cls_id]} {conf:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1),
                      (0, 255, 0), -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
                    cv2.LINE_AA)
        drawn += 1
    return drawn


def main():
    print(f"loading model {MODEL_PATH} ...")
    model = YOLO(MODEL_PATH)
    print("model loaded; classes:", model.names)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, SERVER_PORT))
    print(f"Connected to {SERVER_IP}:{SERVER_PORT}")

    frames = 0
    try:
        while True:
            header = recv_exact(s, 4)
            size = struct.unpack('>I', header)[0]
            if size == 0 or size > 10_000_000:
                print(f"[warn] bad frame size {size}, aborting")
                break

            data = recv_exact(s, size)
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                print("[warn] imdecode failed, skipping")
                continue

            # ---- detection ----
            results = model(frame, conf=CONF_THRES, verbose=False)
            n_det = draw_detections(frame, results)

            frames += 1
            cv2.imshow("RPi Camera + YOLO", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

            if frames % 30 == 0:
                print(f"frames={frames} detections={n_det}")
    except (ConnectionError, KeyboardInterrupt) as e:
        print(f"stopped: {e}")
    finally:
        s.close()
        cv2.destroyAllWindows()
        print(f"total frames received: {frames}")


if __name__ == "__main__":
    main()