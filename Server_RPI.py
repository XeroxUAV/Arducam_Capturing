import cv2, socket, struct, time, traceback
from ultralytics import YOLO

MODEL_PATH = "best.pt"          # change to your file name
CONF_THRES = 0.4                # detection confidence threshold
OUT_W, OUT_H = 640, 480


def open_camera(max_index=10):
    """Return the first /dev/videoN node that can actually stream frames."""
    for index in range(max_index):
        c = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if c.isOpened() and c.read()[0]:
            print(f"using /dev/video{index}", flush=True)
            return c
        c.release()
    raise RuntimeError("no usable V4L2 capture device found")


# ---- Load model ----
print(f"loading model {MODEL_PATH} ...", flush=True)
model = YOLO(MODEL_PATH)
print("model loaded", flush=True)

# ---- Camera ----
cap = open_camera()
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
print("opened:", cap.isOpened(), flush=True)
print(f"capture: {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x"
      f"{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} -> {OUT_W}x{OUT_H}", flush=True)

# ---- Socket ----
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
        ret, frame = cap.read()
        if not ret:
            print(f"[{n}] !! read failed, breaking", flush=True)
            break

        # rotate to match how the camera is mounted
        frame = cv2.rotate(frame, cv2.ROTATE_180)

        # resize to output size BEFORE detection (faster inference)
        if frame.shape[1] != OUT_W or frame.shape[0] != OUT_H:
            frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)

        # ---- Run detection ----
        t0 = time.time()
        results = model(frame, conf=CONF_THRES, verbose=False)
        infer_ms = (time.time() - t0) * 1000

        # ---- Draw boxes ----
        annotated = frame.copy()
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)
            names = results[0].names

            for (x1, y1, x2, y2), conf, cls_id in zip(xyxy, confs, clss):
                label = f"{names[cls_id]} {conf:.2f}"
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # label background
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1),
                              (0, 255, 0), -1)
                cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
                            cv2.LINE_AA)

        # ---- Encode and send ----
        ok, buf = cv2.imencode('.jpg', annotated,
                               [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue
        data = buf.tobytes()
        c.sendall(struct.pack(">L", len(data)) + data)

        print(f"[{n}] detections={len(boxes) if boxes is not None else 0} "
              f"infer={infer_ms:.0f}ms size={len(data)}B", flush=True)
        n += 1

except ConnectionError:
    print("client disconnected", flush=True)
except Exception:
    traceback.print_exc()
finally:
    print("finally: closing", flush=True)
    cap.release(); c.close(); s.close()