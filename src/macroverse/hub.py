import importlib
import os
import signal
import sys
import shutil
from typing import Literal

import httpx
import psutil
import structlog
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
from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .containers.base import Container
from .utils import get_unused_tcp_ports, process_routes


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
        environment_dict = load(environment_yaml, Loader=Loader)
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
            await container.create_environment()
            container.create_time = None
            tg.cancel_scope.cancel()

    async def start_server(self, env_name):
        logger.info(f"Starting server for environment: {env_name}")
        container = self.containers[env_name]
        port = get_unused_tcp_ports(1)[0]
        cmd = container.get_server_command(port)
        process = await open_process(cmd, stdout=None, stderr=None)
        async with httpx.AsyncClient() as client:
            while True:
                await sleep(0.1)
                try:
                    response = await client.get(f"http://127.0.0.1:{port}/routes")
                    break
                except Exception:
                    pass
        routes = response.json()
        container.nginx_conf = NGINX_MAIN_JUPYVERSE_CONF.format(
            uuid=container.id,
            macroverse_port=self.macroverse_port,
            environment_server_port=port,
        ) + process_routes(routes, port, str(container.id))
        container.port = port
        container.process = process
        await self.write_nginx_conf()
        await run_process("nginx -s reload")

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
            nginx_conf = [
                NGINX_CONF.format(
                    nginx_port=self.nginx_port, macroverse_port=self.macroverse_port
                )
            ]
            for name, container in self.containers.items():
                if container.nginx_conf:
                    nginx_conf.append(container.nginx_conf)
            nginx_conf.append("}")
            nginx_conf_str = "".join(nginx_conf)
            await self.nginx_conf_path.write_text(nginx_conf_str)


NGINX_CONF = """\
map $http_upgrade $connection_upgrade {{
    default upgrade;
    ''      close;
}}

server {{
    # nginx at {nginx_port}

    listen       {nginx_port};
    server_name  localhost;

    # macroverse at {macroverse_port}

    location = / {{
        rewrite / /macroverse break;
        proxy_pass http://localhost:{macroverse_port};
    }}

    location /macroverse {{
        proxy_pass http://localhost:{macroverse_port};
    }}
"""


NGINX_MAIN_JUPYVERSE_CONF = """
    # jupyverse in main environment at {macroverse_port}

    location /jupyverse/{uuid} {{
        rewrite ^/jupyverse/{uuid}/(.*)$ /jupyverse/$1 break;
        proxy_pass http://localhost:{macroverse_port};
        proxy_set_header X-Environment-ID {uuid};
    }}
    location ~ ^/jupyverse/{uuid}/terminals/websocket/(.*)$ {{
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        rewrite ^/jupyverse/{uuid}/terminals/websocket/(.*)$ /jupyverse/terminals/websocket/$1 break;
        proxy_pass http://localhost:{macroverse_port};
    }}

    # jupyverse in environment {uuid} at {environment_server_port}
"""
