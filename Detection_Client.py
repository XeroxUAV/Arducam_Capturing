import socket
import struct

import cv2
import numpy as np

SERVER_IP = '10.189.32.248'   # <-- replace with the PI's actual IP
SERVER_PORT = 8080


def recv_exact(sock, n):
    """Receive exactly n bytes or raise."""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed by server")
        buf += chunk
    return buf


def main():
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

            frames += 1
            cv2.imshow("RPi Camera", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break
    except (ConnectionError, KeyboardInterrupt) as e:
        print(f"stopped: {e}")
    finally:
        s.close()
        cv2.destroyAllWindows()
        print(f"total frames received: {frames}")


if __name__ == "__main__":
    main()