import io
import pickle
import socket

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


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def send_request(sock, request_obj):
    stream = io.BytesIO()
    pickle.dump(request_obj, stream)
    payload = stream.getvalue()
    sock.sendall(len(payload).to_bytes(HEADER_SIZE, byteorder="big") + payload)


def receive_response(sock):
    header = recv_exact(sock, HEADER_SIZE)
    if not header:
        return None

    payload_length = int.from_bytes(header, byteorder="big")
    payload = recv_exact(sock, payload_length)
    if payload is None:
        return None

    stream = io.BytesIO(payload)
    response = pickle.load(stream)
    return response.payload


def build_request(command_line):
    parts = command_line.strip().split(maxsplit=2)
    if not parts:
        return None

    command = parts[0].upper()

    if command in ["LIST", "COUNT", "CLEAR", "QUIT"]:
        return Request(command)

    if command in ["GET", "REMOVE", "POP"]:
        key = parts[1] if len(parts) > 1 else None
        return Request(command, key)

    if command in ["ADD", "UPDATE"]:
        key = parts[1] if len(parts) > 1 else None
        value = parts[2] if len(parts) > 2 else None
        return Request(command, key, value)

    return Request(command)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Connected to binary server.")
        print("Commands: ADD, GET, REMOVE, LIST, COUNT, CLEAR, UPDATE, POP, QUIT")

        while True:
            command_line = input("client> ").strip()
            if not command_line:
                continue

            request = build_request(command_line)
            send_request(s, request)
            response = receive_response(s)

            if response is None:
                print("Server closed the connection.")
                break

            print(f"Server response: {response}")

            if command_line.upper() == "QUIT":
                break


if __name__ == "__main__":
    main()
