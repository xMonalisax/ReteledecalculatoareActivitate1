import io
import pickle
import socket
import threading

HOST = "127.0.0.1"
PORT = 3333
BUFFER_SIZE = 1024
HEADER_SIZE = 4


class Response:
    def __init__(self, payload):
        self.payload = payload


class Request:
    def __init__(self, command, key=None, resource=None):
        self.command = command
        self.key = key
        self.resource = resource


class State:
    def __init__(self):
        self.resources = {}
        self.lock = threading.Lock()

    def add(self, key, value):
        with self.lock:
            if key in self.resources:
                return "ERROR key already exists"
            self.resources[key] = value
            return "OK record added"

    def get(self, key):
        with self.lock:
            if key not in self.resources:
                return "ERROR invalid key"
            return f"DATA {self.resources[key]}"

    def remove(self, key):
        with self.lock:
            if key not in self.resources:
                return "ERROR invalid key"
            del self.resources[key]
            return "OK value deleted"

    def list_items(self):
        with self.lock:
            if not self.resources:
                return "DATA|"
            items = [f"{key}={value}" for key, value in self.resources.items()]
            return "DATA|" + ",".join(items)

    def count(self):
        with self.lock:
            return f"DATA {len(self.resources)}"

    def clear(self):
        with self.lock:
            self.resources.clear()
            return "OK all data deleted"

    def update(self, key, value):
        with self.lock:
            if key not in self.resources:
                return "ERROR invalid key"
            self.resources[key] = value
            return "OK Data updated"

    def pop(self, key):
        with self.lock:
            if key not in self.resources:
                return "ERROR invalid key"
            value = self.resources.pop(key)
            return f"DATA {value}"


state = State()


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def send_message(sock, response_obj):
    stream = io.BytesIO()
    pickle.dump(response_obj, stream)
    payload = stream.getvalue()
    sock.sendall(len(payload).to_bytes(HEADER_SIZE, byteorder="big") + payload)


def receive_request(sock):
    header = recv_exact(sock, HEADER_SIZE)
    if not header:
        return None

    payload_length = int.from_bytes(header, byteorder="big")
    payload = recv_exact(sock, payload_length)
    if payload is None:
        return None

    stream = io.BytesIO(payload)
    return pickle.load(stream)


def process_request(request):
    if not isinstance(request, Request):
        return Response("ERROR invalid request"), False

    command = (request.command or "").upper()

    if command == "ADD":
        if not request.key or request.resource is None:
            return Response("ERROR usage: ADD key value"), False
        return Response(state.add(request.key, request.resource)), False

    if command == "GET":
        if not request.key:
            return Response("ERROR usage: GET key"), False
        return Response(state.get(request.key)), False

    if command == "REMOVE":
        if not request.key:
            return Response("ERROR usage: REMOVE key"), False
        return Response(state.remove(request.key)), False

    if command == "LIST":
        return Response(state.list_items()), False

    if command == "COUNT":
        return Response(state.count()), False

    if command == "CLEAR":
        return Response(state.clear()), False

    if command == "UPDATE":
        if not request.key or request.resource is None:
            return Response("ERROR usage: UPDATE key new_value"), False
        return Response(state.update(request.key, request.resource)), False

    if command == "POP":
        if not request.key:
            return Response("ERROR usage: POP key"), False
        return Response(state.pop(request.key)), False

    if command == "QUIT":
        return Response("OK connection closed"), True

    return Response("ERROR unknown command"), False


def handle_client(client_socket, address):
    print(f"[SERVER] Connection from {address}")
    with client_socket:
        while True:
            try:
                request = receive_request(client_socket)
                if request is None:
                    break

                response, should_close = process_request(request)
                send_message(client_socket, response)

                if should_close:
                    break
            except Exception as e:
                send_message(client_socket, Response(f"ERROR {e}"))
                break



def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[SERVER] Listening on {HOST}:{PORT}")

        while True:
            client_socket, address = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, address), daemon=True).start()


if __name__ == "__main__":
    start_server()
