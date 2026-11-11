import cv2
import socket
import struct
import numpy as np
import time
import os

# ============================================================
# Config
# ============================================================
RPI_IP = '10.189.32.248'
PORT = 8080

OUTPUT_DIR = 'pictures'
SAVE_FPS = 5.0                       # target: 5 images per second
SAVE_INTERVAL = 1.0 / SAVE_FPS        # 0.2 s between saves
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# Socket
# ============================================================
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((RPI_IP, PORT))
print(f"Connected to {RPI_IP}:{PORT}")

data = b""
payload_size = struct.calcsize(">L")

# ============================================================
# State
# ============================================================
frame_count = 0
fps_start_time = time.time()
FPS_PRINT_INTERVAL = 1.0
fps_display = 0.0

# Image-saving state
last_save_time = 0.0
saved_count = 0

try:
    while True:
        # ---------- Receive full frame ----------
        while len(data) < payload_size:
            packet = client_socket.recv(4096)
            if not packet: break
            data += packet
        if len(data) < payload_size: break

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]

        while len(data) < msg_size:
            packet = client_socket.recv(4096)
            if not packet: break
            data += packet
        if len(data) < msg_size: break

        frame_data = data[:msg_size]
        data = data[msg_size:]

        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue

        # ---------- FPS calculation ----------
        frame_count += 1
        elapsed = time.time() - fps_start_time
        if elapsed >= FPS_PRINT_INTERVAL:
            fps = frame_count / elapsed
            fps_display = fps
            print(f"FPS: {fps:.1f}  | saved images: {saved_count}")
            frame_count = 0
            fps_start_time = time.time()

        # ---------- Save image every 1/SAVE_FPS seconds ----------
        now = time.time()
        if now - last_save_time >= SAVE_INTERVAL:
            ts = time.strftime('%Y%m%d_%H%M%S', time.localtime(now))
            ms = int((now % 1) * 1000)        # milliseconds for uniqueness
            img_path = os.path.join(OUTPUT_DIR, f'img_{ts}_{ms:03d}.jpg')

            # Save at high quality (95); use .png instead if you want lossless
            cv2.imwrite(img_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_count += 1

            last_save_time = now

        # ---------- Display ----------
        cv2.putText(frame, f"FPS: {fps_display:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"saved: {saved_count}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)

        cv2.imshow('Laptop Receiver', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    client_socket.close()
    cv2.destroyAllWindows()
    print(f"Done. Saved {saved_count} images in '{OUTPUT_DIR}/'")