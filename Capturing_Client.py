import cv2
import socket
import struct
import numpy as np

# Connect to Raspberry Pi IP (replace with actual IP)
RPI_IP = '10.213.29.248' 
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((RPI_IP, 8080))

data = b""
payload_size = struct.calcsize(">L")

while True:
    # Receive complete frame data
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
    
    # Decode and display
    frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    cv2.imshow('Laptop Receiver', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

client_socket.close()
cv2.destroyAllWindows()