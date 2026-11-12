"""YOLO annotation helper for the WebRTC video track."""

from __future__ import annotations

import time

import cv2

DEFAULT_MODEL = "Window_Arducam.pt"
CONF_THRES = 0.4


def make_annotator(model_path: str = DEFAULT_MODEL, conf: float = CONF_THRES):
    """Load a YOLO model and return a frame -> annotated frame callable."""
    from ultralytics import YOLO

    print(f"loading model {model_path} ...", flush=True)
    model = YOLO(model_path)
    print("model loaded", flush=True)

    def annotate(frame):
        t0 = time.time()
        results = model(frame, conf=conf, verbose=False)
        infer_ms = (time.time() - t0) * 1000

        annotated = frame.copy()
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)
            names = results[0].names

            for (x1, y1, x2, y2), box_conf, cls_id in zip(xyxy, confs, clss):
                label = f"{names[cls_id]} {box_conf:.2f}"
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                (tw, th), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                cv2.rectangle(
                    annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 255, 0), -1
                )
                cv2.putText(
                    annotated,
                    label,
                    (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1,
                    cv2.LINE_AA,
                )

        count = 0 if boxes is None else len(boxes)
        print(f"detections={count} infer={infer_ms:.0f}ms", flush=True)
        return annotated

    return annotate
