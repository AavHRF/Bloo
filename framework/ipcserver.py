import socket
import threading


class IPCServer:
    def __init__(self, port, handler):
        self.port = port
        self.handler = handler
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("localhost", port))
        self.server.listen(1)
        self.server.settimeout(1)
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        while True:
            try:
                conn, addr = self.server.accept()
                data = conn.recv(1024)
                if data:
                    self.handler(data)
            except socket.timeout:
                pass
