import webbrowser
from collections.abc import Callable
from functools import partial
from typing import Any

from anyio import Event, create_task_group, sleep_forever
from anyio.abc import TaskStatus
from fastapi import Request
from fps import Context, Module, get_nowait, get_root_module, put
from jupyverse_api.auth import AuthConfig
from jupyverse_api.lab import PageConfig
from fastapi import FastAPI
from structlog import get_logger

from .hub import ContainerType, Hub
from .ui.main import macroverse_app
from .utils import get_unused_tcp_ports


logger = get_logger()


class MacroverseModule(Module):
    def __init__(
        self,
        container: ContainerType,
        open_browser: bool,
    ):
        super().__init__(
            "macroverse", prepare_timeout=10, start_timeout=10, stop_timeout=10
        )
        self.container = container
        self.open_browser = open_browser
        self.host = "localhost"
        self.nginx_port, self.macroverse_port = get_unused_tcp_ports(2)
        self.add_module("fps.web.fastapi:FastAPIModule", "fastapi")
        self.add_module(
            "fps.web.server:ServerModule",
            "server",
            host=self.host,
            port=self.macroverse_port,
        )

    async def prepare(self):
        async with create_task_group() as tg:
            root_app = await self.get(FastAPI)
            root_app.mount("/macroverse", macroverse_app)
            self.hub = Hub(tg, self.nginx_port, self.macroverse_port, self.container)

            @macroverse_app.middleware("http")
            async def put_hub(
                request: Request, call_next: Callable[[Request], Any]
            ) -> Any:
                async with Context():
                    put(self.hub)
                    response = await call_next(request)
                    return response

            jupyverse_modules = {
                name: {"type": name}
                for name in [
                    "frontend",
                    "yjs",
                    "jupyterlab",
                    "file_id",
                    "nbconvert",
                    "app",
                    "page_config",
                    "lab",
                    "auth",
                    "contents",
                    "file_watcher",
                ]
            }
            jupyverse_modules["frontend"]["config"] = {"base_url": "/jupyverse/"}
            jupyverse_modules["page_config_hook"] = {"type": PageConfigHookModule}
            config = {
                "jupyverse": {
                    "type": "jupyverse_api.main:JupyverseModule",
                    "modules": jupyverse_modules,
                    "config": {"start_server": False},
                }
            }
            jupyverse_module = get_root_module(config)
            stop_event = Event()
            await tg.start(self._run_jupyverse, jupyverse_module, stop_event)
            root_app.mount("/jupyverse", jupyverse_module.app)  # type: ignore[attr-defined]

            self.add_teardown_callback(stop_event.set)
            self.done()
            await sleep_forever()

    async def start(self):
        async with create_task_group() as tg:
            tg.start_soon(super().start)
            await self.modules["server"].started.wait()
            url = f"http://{self.host}:{self.nginx_port}"
            logger.info("Macroverse running", url=url)
            if self.open_browser:
                webbrowser.open_new_tab(url)

    async def _run_jupyverse(
        self,
        jupyverse_module: Module,
        stop_event: Event,
        *,
        task_status: TaskStatus[None],
    ) -> None:
        async with jupyverse_module:
            auth_config = await jupyverse_module.get(AuthConfig)
            self.hub.auth_token = auth_config.token  # type: ignore[attr-defined]
            task_status.started()
            await stop_event.wait()

    async def stop(self) -> None:
        await self.hub.stop()


async def hook(auth_token: str, config: dict[str, Any]) -> None:
    with get_nowait(Request) as request:
        uuid = request.headers["x-environment-id"]
        jupyverse_len = len("/jupyverse")
        for key, val in config.items():
            if isinstance(val, str) and val.startswith("/jupyverse"):
                config[key] = f"/jupyverse/{uuid}" + val[jupyverse_len:]
        config["token"] = auth_token


class PageConfigHookModule(Module):
    async def prepare(self) -> None:
        auth_config = await self.get(AuthConfig)
        page_config = await self.get(PageConfig)
        page_config.register(partial(hook, auth_config.token))  # type: ignore[attr-defined]
