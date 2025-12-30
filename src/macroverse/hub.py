import os
import signal
import sys
from typing import Any
from uuid import uuid4

import anyio
import httpx
import psutil
import structlog
import yaml
from anyio import (
    Lock,
    NamedTemporaryFile,
    create_task_group,
    open_process,
    run_process,
    sleep,
)
from anyio.abc import Process, TaskGroup
from pydantic import BaseModel, Field, UUID4

from .utils import get_unused_tcp_ports


logger = structlog.get_logger()


class Hub:
    def __init__(
        self, task_group: TaskGroup, nginx_port: int, macroverse_port: int
    ) -> None:
        self.task_group = task_group
        self.nginx_port = nginx_port
        self.macroverse_port = macroverse_port
        self.lock = Lock()
        self.environments: dict[str, Environment] = {}
        self.nginx_conf_path = (
            anyio.Path(sys.prefix) / "etc" / "nginx" / "sites.d" / "default-site.conf"
        )
        task_group.start_soon(self.start)

    async def start(self) -> None:
        env_dir = anyio.Path("environments")
        if await env_dir.is_dir():
            async for env_path in env_dir.iterdir():
                self.environments[env_path.name] = Environment()
        await self.write_nginx_conf()
        logger.info("Starting nginx")
        self.nginx_process = await open_process("nginx")

    async def stop(self) -> None:
        async with create_task_group() as tg:
            for name in self.environments:
                tg.start_soon(self.stop_server, name)
        try:
            logger.info("Stopping nginx")
            await run_process("nginx -s stop")
        except Exception:
            pass

    async def create_environment(self, environment_yaml: str) -> None:
        environment = yaml.load(environment_yaml, Loader=yaml.CLoader)
        self.environments[environment["name"]] = _environment = Environment(
            create_time=0
        )
        self.task_group.start_soon(self._create_environment, environment, _environment)

    async def _run_time(self, environment: "Environment") -> None:
        while True:
            await sleep(1)
            assert environment.create_time is not None
            environment.create_time += 1

    async def _create_environment(
        self, environment_yaml: dict[str, Any], environment: "Environment"
    ) -> None:
        async with create_task_group() as tg:
            tg.start_soon(self._run_time, environment)
            server_env_path = anyio.Path("environments") / environment_yaml["name"]
            if not await server_env_path.exists():
                environment_yaml["dependencies"].extend(
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
                environment_str = yaml.dump(environment_yaml, Dumper=yaml.CDumper)
                async with NamedTemporaryFile(
                    mode="wb", buffering=0, delete=True, suffix=".yaml"
                ) as f:
                    await f.write(environment_str.encode())
                    create_environment_cmd = (
                        f"micromamba create -f {f.name} -p {server_env_path} --yes"
                    )
                    await run_process(create_environment_cmd)
                    environment.create_time = None
                    tg.cancel_scope.cancel()

    async def start_server(self, env_name):
        port = get_unused_tcp_ports(1)[0]
        environment = self.environments[env_name]
        launch_jupyverse_cmd = f"jupyverse --port {port} --set frontend.base_url=/jupyverse/{environment.id}/"
        cmd = (
            """bash -c 'eval "$(micromamba shell hook --shell bash)";"""
            + f"micromamba activate environments/{env_name};"
            + f"{launch_jupyverse_cmd}'"
        )
        environment.process = await open_process(cmd, stdout=None, stderr=None)
        environment.port = port
        await self.write_nginx_conf()
        await run_process("nginx -s reload")
        async with httpx.AsyncClient() as client:
            while True:
                await sleep(0.1)
                try:
                    await client.get(f"http://127.0.0.1:{port}")
                except httpx.ConnectError:
                    pass
                else:
                    return

    async def stop_server(self, env_name: str) -> None:
        environment = self.environments[env_name]
        if environment.process is None:
            return

        logger.info(f"Stopping server for environment: {env_name}")
        process = psutil.Process(environment.process.pid)
        children = process.children(recursive=True)
        if children:
            os.kill(children[0].pid, signal.SIGINT)
        await environment.process.wait()
        environment.process = None

    async def write_nginx_conf(self) -> None:
        async with self.lock:
            nginx_conf = NGINX_CONF.replace("NGINX_PORT", str(self.nginx_port)).replace(
                "MACROVERSE_PORT", str(self.macroverse_port)
            )
            for name, environment in self.environments.items():
                if environment.process is not None:
                    nginx_kernel_conf = (
                        NGINX_KERNEL_CONF.replace(
                            "KERNEL_SERVER_PORT", str(environment.port)
                        )
                        .replace("MACROVERSE_PORT", str(self.macroverse_port))
                        .replace("UUID", str(environment.id))
                    )
                    nginx_conf = nginx_conf.replace(
                        "# NGINX_KERNEL_CONF", nginx_kernel_conf
                    )
            await self.nginx_conf_path.write_text(nginx_conf)


class Environment(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    port: int | None = None
    process: Process | None = None
    create_time: int | None = None

    class Config:
        arbitrary_types_allowed = True


NGINX_CONF = """
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
        proxy_set_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # jupyverse kernel servers
# NGINX_KERNEL_CONF

}
"""


NGINX_KERNEL_CONF = """
    location /jupyverse/UUID {
        rewrite ^/jupyverse/UUID/(.*)$ /jupyverse/$1 break;
        rewrite /jupyverse/UUID /jupyverse/lab break;
        proxy_pass http://localhost:MACROVERSE_PORT;
        proxy_set_header X-Environment-ID UUID;
    }
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
        proxy_set_header Host $host;
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
