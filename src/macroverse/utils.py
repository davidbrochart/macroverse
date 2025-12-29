from socket import socket


def get_unused_tcp_ports(number: int) -> list[int]:
    try:
        sockets = []
        for _ in range(number):
            sock = socket()
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()
