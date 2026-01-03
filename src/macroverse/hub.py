import importlib
import os
import signal
import sys
import shutil
from typing import Literal

import httpx
import psutil
import structlog
import yaml
from anyio import (
    Lock,
    Path,
    create_task_group,
    open_process,
    run_process,
    sleep,
    to_thread,
)
from anyio.abc import TaskGroup

from .containers.base import Container
from .utils import get_unused_tcp_ports


ContainerType = Literal["process", "docker"]
logger = structlog.get_logger()


class Hub:
    def __init__(
        self,
        task_group: TaskGroup,
        nginx_port: int,
        macroverse_port: int,
        container_name: ContainerType,
    ) -> None:
        self.task_group = task_group
        self.nginx_port = nginx_port
        self.macroverse_port = macroverse_port
        self.container_name = container_name
        self.auth_token = None
        self.lock = Lock()
        self.containers: dict[str, Container] = {}
        self.nginx_conf_path = (
            Path(sys.prefix) / "etc" / "nginx" / "sites.d" / "default-site.conf"
        )
        self.Container = importlib.import_module(
            f".containers.{container_name}", package="macroverse"
        ).Container
        task_group.start_soon(self.start)

    async def start(self) -> None:
        env_dir = Path("environments")
        if await env_dir.is_dir():
            async for env_path in env_dir.iterdir():
                container = await self.Container.from_existing_environment(env_path)
                self.containers[env_path.name] = container
        await self.write_nginx_conf()
        await open_process("nginx")
        logger.info("Starting nginx")

    async def stop(self) -> None:
        async with create_task_group() as tg:
            for name in self.containers:
                tg.start_soon(self.stop_server, name, False)
        try:
            logger.info("Stopping nginx")
            await run_process("nginx -s stop")
        except Exception:
            pass

    async def create_environment(self, environment_yaml: str) -> None:
        environment_dict = yaml.load(environment_yaml, Loader=yaml.CLoader)
        env_name = environment_dict["name"]
        env_path = Path("environments") / env_name
        if await env_path.exists():
            logger.info(f"Environment already exists: {env_name}")
            return

        logger.info(f"Creating environment: {env_name}")
        self.containers[env_name] = container = self.Container(
            create_time=0, definition=environment_dict, path=env_path
        )
        self.task_group.start_soon(self._create_environment, container)

    async def _creation_timer(self, container: Container) -> None:
        while True:
            await sleep(1)
            assert container.create_time is not None
            container.create_time += 1

    async def _create_environment(self, container: Container) -> None:
        async with create_task_group() as tg:
            tg.start_soon(self._creation_timer, container)
            assert container.definition is not None
            container.definition["dependencies"].extend(
                [
                    "rich-click",
                    "anycorn",
                    "jupyverse-api",
                    "fps-file-watcher",
                    "fps-kernels",
                    "fps-kernel-subprocess",
                    "fps-noauth",
                    "fps-frontend",
                ]
            )
            await container.create_environment()
            container.create_time = None
            tg.cancel_scope.cancel()

    async def start_server(self, env_name):
        logger.info(f"Starting server for environment: {env_name}")
        container = self.containers[env_name]
        port = get_unused_tcp_ports(1)[0]
        cmd = container.get_server_command(port)
        process = await open_process(cmd, stdout=None, stderr=None)
        container.port = (
            port  # port must be set before writing NGINX conf, but not process!
        )
        await self.write_nginx_conf()
        await run_process("nginx -s reload")
        async with httpx.AsyncClient() as client:
            while True:
                await sleep(0.1)
                try:
                    await client.get(f"http://127.0.0.1:{port}")
                except Exception:
                    pass
                else:
                    break
        container.process = process

    async def stop_server(self, env_name: str, reload_nginx: bool = True) -> None:
        container = self.containers[env_name]
        if container.process is None:
            return

        logger.info(f"Stopping server for environment: {env_name}")
        process = psutil.Process(container.process.pid)
        children = process.children(recursive=True)
        if children:
            os.kill(children[0].pid, signal.SIGINT)
        await container.process.wait()
        container.process = None
        container.port = None
        await self.write_nginx_conf()
        if reload_nginx:
            await run_process("nginx -s reload")

    async def delete_environment(self, env_name: str) -> None:
        await self.stop_server(env_name)
        logger.info(f"Deleting environment: {env_name}")
        del self.containers[env_name]
        env_dir = Path("environments") / env_name
        await to_thread.run_sync(shutil.rmtree, env_dir)
        await self.write_nginx_conf()

    async def write_nginx_conf(self) -> None:
        async with self.lock:
            nginx_conf = NGINX_CONF.replace("NGINX_PORT", str(self.nginx_port)).replace(
                "MACROVERSE_PORT", str(self.macroverse_port)
            )
            for name, container in self.containers.items():
                if container.port is not None:
                    nginx_kernel_conf = (
                        NGINX_KERNEL_CONF.replace(
                            "KERNEL_SERVER_PORT", str(container.port)
                        )
                        .replace("MACROVERSE_PORT", str(self.macroverse_port))
                        .replace("UUID", str(container.id))
                    )
                    nginx_conf = nginx_conf.replace(
                        "# NGINX_KERNEL_CONF", nginx_kernel_conf
                    )
            await self.nginx_conf_path.write_text(nginx_conf)


NGINX_CONF = """\
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    # nginx at NGINX_PORT
    listen       NGINX_PORT;
    server_name  localhost;

    # macroverse at MACROVERSE_PORT
    location = / {
        rewrite / /macroverse break;
        proxy_pass http://localhost:MACROVERSE_PORT;
    }

    location /macroverse {
        proxy_pass http://localhost:MACROVERSE_PORT;
    }

    # jupyverse kernel servers

# NGINX_KERNEL_CONF

}
"""


NGINX_KERNEL_CONF = """
    # main jupyverse at MACROVERSE_PORT
    location /jupyverse/UUID {
        rewrite ^/jupyverse/UUID/(.*)$ /jupyverse/$1 break;
        proxy_pass http://localhost:MACROVERSE_PORT;
        proxy_set_header X-Environment-ID UUID;
    }
    location ~ ^/jupyverse/UUID/terminals/websocket/(.*)$ {
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        rewrite ^/jupyverse/UUID/terminals/websocket/(.*)$ /jupyverse/terminals/websocket/$1 break;
        proxy_pass http://localhost:MACROVERSE_PORT;
    }

    # jupyverse kernels at KERNEL_SERVER_PORT
    location /jupyverse/UUID/kernelspecs {
        rewrite ^/jupyverse/UUID/kernelspecs/(.*)$ /kernelspecs/$1 break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }
    location /jupyverse/UUID/api/kernelspecs {
        rewrite /jupyverse/UUID/api/kernelspecs /api/kernelspecs break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }
    location /jupyverse/UUID/api/kernels {
        rewrite /jupyverse/UUID/api/kernels /api/kernels break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }
    location ~ ^/jupyverse/UUID/api/kernels/(.*)$ {
        if ($http_upgrade != "websocket") {
            rewrite ^/jupyverse/UUID/api/kernels/(.*)$ /api/kernels/$1 break;
            proxy_pass http://localhost:KERNEL_SERVER_PORT;
            break;
        }
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        rewrite ^/jupyverse/UUID/api/kernels/(.*)$ /api/kernels/$1 break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }
    location /jupyverse/UUID/api/sessions {
        rewrite /jupyverse/UUID/api/sessions /api/sessions break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }
    location ~ ^/jupyverse/UUID/api/sessions/(.*)$ {
        rewrite ^/jupyverse/UUID/api/sessions/(.*)$ /api/sessions/$1 break;
        proxy_pass http://localhost:KERNEL_SERVER_PORT;
    }

# NGINX_KERNEL_CONF
"""
