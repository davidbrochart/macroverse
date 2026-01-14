import re
import string
from socket import socket
from typing import Any


_remove_converter_pattern = re.compile(r":\w+}")
_formatter = string.Formatter()


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


def process_routes(
    routes: list[dict[str, Any]], environment_server_port: int, uuid: str
) -> str:
    http_redirects = {}
    ws_redirects = {}
    for route in routes:
        path = _remove_converter_pattern.sub("}", route["path"])
        names = [v[1] for v in _formatter.parse(path) if v[1] is not None]
        src = _formatter.vformat(path, [], {name: "(.*)" for name in names})
        dst = _formatter.vformat(
            path, [], {name: f"${i + 1}" for i, name in enumerate(names)}
        )
        methods = route["methods"]
        if methods == ["WEBSOCKET"]:
            ws_redirects[src] = (dst, methods)
        else:
            http_redirects[src] = (dst, methods)
    redirects = []
    for src, val in ws_redirects.items():
        dst, methods = val
        redirects.append(
            NGINX_REDIRECT_WS.format(
                uuid=uuid,
                src=src,
                dst=dst,
                methods=methods,
                environment_server_port=environment_server_port,
            )
        )
    for src, val in http_redirects.items():
        dst, methods = val
        redirects.append(
            NGINX_REDIRECT_HTTP.format(
                uuid=uuid,
                src=src,
                dst=dst,
                methods=methods,
                environment_server_port=environment_server_port,
            )
        )
    return "".join(redirects)


NGINX_REDIRECT_HTTP = """
    # redirect {methods} {src}
    location ~ ^/jupyverse/{uuid}{src}$ {{
        rewrite ^/jupyverse/{uuid}{src} {dst} break;
        proxy_pass http://localhost:{environment_server_port};
    }}
"""


NGINX_REDIRECT_WS = """
    # redirect {methods} {src}
    location ~ ^/jupyverse/{uuid}{src}$ {{
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        rewrite ^/jupyverse/{uuid}{src} {dst} break;
        proxy_pass http://localhost:{environment_server_port};
    }}
"""
