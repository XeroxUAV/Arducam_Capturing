import cv2
import socket
import struct
import numpy as np
import time

RPI_IP = '10.213.29.248'
PORT = 8080

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((RPI_IP, PORT))

data = b""
payload_size = struct.calcsize(">L")

# ---- FPS tracking ----
frame_count = 0
fps_start_time = time.time()
FPS_PRINT_INTERVAL = 1.0   # print every 1 second
fps_display = 0.0
try:
    while True:
        # Receive complete frame data (unchanged)
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

        frame_data = data[:msg_size]
        data = data[msg_size:]

        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

        # ---- FPS calculation ----
        frame_count += 1
        elapsed = time.time() - fps_start_time
        if elapsed >= FPS_PRINT_INTERVAL:
            fps = frame_count / elapsed
            fps_display = fps
            print(f"FPS: {fps:.1f}")
            frame_count = 0
            fps_start_time = time.time()
        cv2.putText(frame, f"FPS: {fps_display:.1f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.imshow('Laptop Receiver', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    client_socket.close()
    cv2.destroyAllWindows()