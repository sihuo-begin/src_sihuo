import socket
import threading
import time


class TCPClient:
    def __init__(self, host, port, timeout=5, buffer_size=1024):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.sock = None
        self.lock = threading.Lock()

    def connect(self):
        with self.lock:
            if self.sock is not None:
                return
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port))
            except socket.timeout:
                raise TimeoutError(f"Connection to {self.host}:{self.port} timed out")
            except Exception as e:
                raise ConnectionError(f"Could not connect: {e}")

    def disconnect(self):
        with self.lock:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                finally:
                    self.sock = None

    def send(self, data):
        if not self.sock:
            raise ConnectionError("Socket is not connected")
        try:
            self.sock.sendall(data)
        except socket.timeout:
            raise TimeoutError("Send operation timed out")
        except Exception as e:
            raise ConnectionError(f"Send failed: {e}")

    def receive(self):
        if not self.sock:
            raise ConnectionError("Socket is not connected")
        try:
            return self.sock.recv(self.buffer_size)
        except socket.timeout:
            raise TimeoutError("Receive operation timed out")
        except Exception as e:
            raise ConnectionError(f"Receive failed: {e}")

    def send_receive(self, data):
        self.send(data)
        time.sleep(0.05)
        return self.receive()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


#
# if __name__ == "__main__":
#     client = TCPClient("192.168.1.10", 5000, timeout=3, buffer_size=2048)
#     try:
#         client.connect()
#         response = client.send_receive(b"Hello, device?")
#         print("Received:", response)
#     except Exception as e:
#         print("Error:", e)
#     finally:
#         client.disconnect()
