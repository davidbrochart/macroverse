from dataclasses import dataclass, field
from uuid import uuid4

from .containers.base import Container
from .utils import process_routes


@dataclass
class Server:
    macroverse_port: int
    id: str = field(init=False)
    environments: set[str] = field(default_factory=set)
    nginx_conf: str = field(init=False)

    def __post_init__(self):
        self.id = str(uuid4())
        self.nginx_conf = NGINX_MAIN_JUPYVERSE_CONF.format(
            uuid=self.id, macroverse_port=self.macroverse_port
        )

    def create_nginx_conf(self, containers: dict[str, Container]) -> None:
        nginx_confs = [
            NGINX_MAIN_JUPYVERSE_CONF.format(
                uuid=self.id, macroverse_port=self.macroverse_port
            )
        ]
        for env_name in self.environments:
            container = containers[env_name]
            assert container.port is not None
            nginx_confs.append(
                process_routes(container.routes, container.port, self.id)
            )
            nginx_confs.append(
                process_routes(container.routes, container.port, str(container.id))
            )
        self.nginx_conf = "".join(nginx_confs)


NGINX_MAIN_JUPYVERSE_CONF = """
    # jupyverse in main environment at {macroverse_port}

    location /jupyverse/{uuid} {{
        rewrite ^/jupyverse/{uuid}/(.*)$ /jupyverse/$1 break;
        proxy_pass http://localhost:{macroverse_port};
        proxy_set_header X-Environment-ID {uuid};

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }}
"""
