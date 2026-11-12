import socket
import struct
import time

import cv2
from picamera2 import Picamera2

HOST = '0.0.0.0'
PORT = 8080
JPEG_QUALITY = 80
FRAME_W, FRAME_H = 640, 480


def main():
    # ---- Camera setup (Picamera2, not OpenCV VideoCapture) ----
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (FRAME_W, FRAME_H), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # let AE/AWB settle
    print("Camera started")

    # ---- Socket setup ----
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Waiting for laptop connection on {PORT}...")

    conn = None
    try:
        conn, addr = s.accept()
        print(f"Connected: {addr}")

        frame_count = 0
        while True:
            frame = picam2.capture_array()  # RGB numpy array
            # Picamera2 RGB888 is already RGB; OpenCV encode expects BGR
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            ok, buf = cv2.imencode(
                '.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            )
            if not ok:
                print("[warn] imencode failed, skipping frame")
                continue

            data = buf.tobytes()
            header = struct.pack('<I', len(data))  # 4-byte little-endian length

            conn.sendall(header + data)
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"sent {frame_count} frames")

    except (BrokenPipeError, ConnectionResetError):
        print("Client disconnected")
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        print("finally: closing")
        if conn is not None:
            conn.close()
        s.close()
        picam2.stop()


if __name__ == "__main__":
    main()