import socket
import threading

HOST = "127.0.0.1"
PORT = 3333
BUFFER_SIZE = 1024


class State:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def add(self, key, value):
        with self.lock:
            if key in self.data:
                return "ERROR key already exists"
            self.data[key] = value
            return "OK record added"

    def get(self, key):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            return f"DATA {self.data[key]}"

    def remove(self, key):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            del self.data[key]
            return "OK value deleted"

    def list_items(self):
        with self.lock:
            if not self.data:
                return "DATA|"
            items = [f"{key}={value}" for key, value in self.data.items()]
            return "DATA|" + ",".join(items)

    def count(self):
        with self.lock:
            return f"DATA {len(self.data)}"

    def clear(self):
        with self.lock:
            self.data.clear()
            return "OK all data deleted"

    def update(self, key, value):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            self.data[key] = value
            return "OK Data updated"

    def pop(self, key):
        with self.lock:
            if key not in self.data:
                return "ERROR invalid key"
            value = self.data.pop(key)
            return f"DATA {value}"


state = State()


def process_command(command):
    if not command:
        return "ERROR empty command", False

    parts = command.split(maxsplit=2)
    cmd = parts[0].upper()

    if cmd == "ADD":
        if len(parts) < 3:
            return "ERROR usage: ADD key value", False
        key = parts[1]
        value = parts[2]
        return state.add(key, value), False

    if cmd == "GET":
        if len(parts) != 2:
            return "ERROR usage: GET key", False
        return state.get(parts[1]), False

    if cmd == "REMOVE":
        if len(parts) != 2:
            return "ERROR usage: REMOVE key", False
        return state.remove(parts[1]), False

    if cmd == "LIST":
        if len(parts) != 1:
            return "ERROR usage: LIST", False
        return state.list_items(), False

    if cmd == "COUNT":
        if len(parts) != 1:
            return "ERROR usage: COUNT", False
        return state.count(), False

    if cmd == "CLEAR":
        if len(parts) != 1:
            return "ERROR usage: CLEAR", False
        return state.clear(), False

    if cmd == "UPDATE":
        if len(parts) < 3:
            return "ERROR usage: UPDATE key new_value", False
        key = parts[1]
        value = parts[2]
        return state.update(key, value), False

    if cmd == "POP":
        if len(parts) != 2:
            return "ERROR usage: POP key", False
        return state.pop(parts[1]), False

    if cmd == "QUIT":
        return "OK connection closed", True

    return "ERROR unknown command", False



def send_response(client_socket, response):
    response_data = f"{len(response)} {response}".encode("utf-8")
    client_socket.sendall(response_data)



def handle_client(client_socket):
    with client_socket:
        while True:
            try:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break

                command = data.decode("utf-8").strip()
                response, should_close = process_command(command)
                send_response(client_socket, response)

                if should_close:
                    break

            except Exception as e:
                send_response(client_socket, f"ERROR {str(e)}")
                break



def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[SERVER] Listening on {HOST}:{PORT}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"[SERVER] Connection from {addr}")
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()


if __name__ == "__main__":
    start_server()
