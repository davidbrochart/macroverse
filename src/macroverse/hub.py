import os
import signal
import sys
import shutil
from typing import Any, Literal
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
    to_thread,
)
from anyio.abc import Process, TaskGroup
from pydantic import BaseModel, Field, UUID4

from .utils import get_unused_tcp_ports


ContainerType = Literal["process", "docker"]
logger = structlog.get_logger()


class Hub:
    def __init__(
        self,
        task_group: TaskGroup,
        nginx_port: int,
        macroverse_port: int,
        container: ContainerType,
    ) -> None:
        self.task_group = task_group
        self.nginx_port = nginx_port
        self.macroverse_port = macroverse_port
        self.container = container
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
                if self.container == "process":
                    environment = Environment()
                elif self.container == "docker":
                    dockerfile = await (env_path / "Dockerfile").read_text()
                    environment_id = dockerfile.splitlines()[-1][2:]
                    environment = Environment(id=environment_id)
                self.environments[env_path.name] = environment
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

    async def _creation_timer(self, environment: "Environment") -> None:
        while True:
            await sleep(1)
            assert environment.create_time is not None
            environment.create_time += 1

    async def _create_environment(
        self, environment_yaml: dict[str, Any], environment: "Environment"
    ) -> None:
        async with create_task_group() as tg:
            tg.start_soon(self._creation_timer, environment)
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
                if self.container == "docker":
                    environment_yaml["name"] = "base"
                environment_str = yaml.dump(environment_yaml, Dumper=yaml.CDumper)
                if self.container == "process":
                    async with NamedTemporaryFile(
                        mode="wb", buffering=0, suffix=".yaml"
                    ) as environment_file:
                        await environment_file.write(environment_str.encode())
                        create_environment_cmd = f"micromamba create -f {environment_file.name} -p {server_env_path} --yes"
                        await run_process(create_environment_cmd)
                elif self.container == "docker":
                    await server_env_path.mkdir(parents=True)
                    await (server_env_path / "environment.yaml").write_text(
                        environment_str
                    )
                    dockerfile_str = DOCKERFILE.replace(
                        "ENVIRONMENT_PATH", "environment.yaml"
                    ).replace("ENVIRONMENT_ID", str(environment.id))
                    await (server_env_path / "Dockerfile").write_text(dockerfile_str)
                    build_docker_image_cmd = (
                        f"docker build --tag {environment.id} {server_env_path}"
                    )
                    await run_process(build_docker_image_cmd, stdout=None, stderr=None)
                environment.create_time = None
                tg.cancel_scope.cancel()

    async def start_server(self, env_name):
        environment = self.environments[env_name]
        port = get_unused_tcp_ports(1)[0]
        if self.container == "process":
            launch_jupyverse_cmd = f"jupyverse --port {port} --set frontend.base_url=/jupyverse/{environment.id}/"
            cmd = (
                """bash -c 'eval "$(micromamba shell hook --shell bash)";"""
                + f"micromamba activate environments/{env_name};"
                + f"{launch_jupyverse_cmd}'"
            )
        elif self.container == "docker":
            launch_jupyverse_cmd = f"jupyverse --host 0.0.0.0 --port 5000 --set frontend.base_url=/jupyverse/{environment.id}/"
            cmd = f"docker run -p {port}:5000 {environment.id} {launch_jupyverse_cmd}"
        process = await open_process(cmd, stdout=None, stderr=None)
        environment.port = (
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
        environment.process = process

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

    async def delete_environment(self, env_name: str) -> None:
        await self.stop_server(env_name)
        logger.info(f"Deleting environment: {env_name}")
        del self.environments[env_name]
        env_dir = anyio.Path("environments") / env_name
        await to_thread.run_sync(shutil.rmtree, env_dir)

    async def write_nginx_conf(self) -> None:
        async with self.lock:
            nginx_conf = NGINX_CONF.replace("NGINX_PORT", str(self.nginx_port)).replace(
                "MACROVERSE_PORT", str(self.macroverse_port)
            )
            for name, environment in self.environments.items():
                if environment.port is not None:
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
    id: UUID4 | str = Field(default_factory=uuid4)
    port: int | None = None
    process: Process | None = None
    create_time: int | None = None

    class Config:
        arbitrary_types_allowed = True


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
        proxy_set_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # jupyverse kernel servers

# NGINX_KERNEL_CONF

}
"""


NGINX_KERNEL_CONF = """
    # main jupyverse at MACROVERSE_PORT
    location /jupyverse/UUID {
        rewrite ^/jupyverse/UUID/(.*)$ /jupyverse/$1 break;
        rewrite /jupyverse/UUID /jupyverse/lab break;
        proxy_pass http://localhost:MACROVERSE_PORT;
        proxy_set_header X-Environment-ID UUID;
    }
    location ~ ^/jupyverse/UUID/terminals/websocket/(.*)$ {
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        rewrite ^/jupyverse/UUID/terminals/websocket/(.*)$ /jupyverse/terminals/websocket/$1 break;
        proxy_pass http://localhost:MACROVERSE_PORT;
    }

    # jupyverse kernels ar KERNEL_SERVER_PORT
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


DOCKERFILE = """\
FROM mambaorg/micromamba:2.4.0

COPY --chown=$MAMBA_USER:$MAMBA_USER ENVIRONMENT_PATH /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml &&  micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1
EXPOSE 5000
# ENVIRONMENT_ID
"""
