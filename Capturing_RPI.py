import cv2
import socket
import struct

# Output size sent to the laptop. The Arducam B0495 only exposes 1920x1200
# and 960x600 natively, so capture at 960x600 and downscale to 640x480.
OUT_W, OUT_H = 640, 480

# 1. Initialize camera
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
print(f"capture: {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x"
      f"{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} -> {OUT_W}x{OUT_H}")

# 2. Establish Socket connection
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 8080)) # Listen on port 8080
server_socket.listen(1)
print("Waiting for laptop connection...")

client_socket, addr = server_socket.accept()
print(f"Connected: {addr}")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if frame.shape[1] != OUT_W or frame.shape[0] != OUT_H:
        frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
    frame = cv2.rotate(frame, cv2.ROTATE_180)
    # Compress to JPEG to reduce bandwidth usage
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    data = buffer.tobytes()
    
    # Send data length first (for the receiving end to parse the complete frame)
    client_socket.sendall(struct.pack(">L", len(data)) + data)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
client_socket.close()
server_socket.close()