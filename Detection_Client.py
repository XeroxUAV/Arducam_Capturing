import cv2
import socket
import struct
import numpy as np

# Configuration
SERVER_IP = '192.168.1.100'  # <-- Replace with your Pi's IP address
SERVER_PORT = 8080

def recvall(sock, n):
    """Helper function to receive exactly n bytes."""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

# Connect to the server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(f"Connecting to {SERVER_IP}:{SERVER_PORT}...")
client_socket.connect((SERVER_IP, SERVER_PORT))
print("Connected!")

try:
    while True:
        # Read the 4-byte length header
        header = recvall(client_socket, struct.calcsize(">L"))
        if header is None:
            print("Connection closed by server.")
            break

        # Unpack length and read the JPEG data
        (frame_size,) = struct.unpack(">L", header)
        frame_data = recvall(client_socket, frame_size)
        if frame_data is None:
            print("Connection closed while reading frame.")
            break

        # Decode JPEG -> numpy array
        np_data = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

        if frame is None:
            print("Failed to decode frame.")
            continue

        # Show frame
        cv2.imshow("Pi Camera Stream", frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Interrupted by user.")

finally:
    client_socket.close()
    cv2.destroyAllWindows()
    print("Disconnected.")