import cv2
import socket
import struct

# 1. Initialize camera
cap = cv2.VideoCapture(0) 

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