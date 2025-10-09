from importlib.metadata import entry_points
from uuid import uuid4

from anyio import Event, TASK_STATUS_IGNORED, sleep_forever
from anyio.abc import TaskStatus
from fastapi.responses import HTMLResponse, RedirectResponse
from fps import get_root_module
from jupyverse_api import Router
from jupyverse_api.app import App
from jupyverse_api.auth import Auth, User


class Macroverse:
    def __init__(self, app, tg):
        self.jupyverses = []

        @app.get("/", response_class=HTMLResponse)
        async def get_root():
            return """
            <html>
                <head>
                    <title>Macroverse</title>
                </head>
                <body>
                    <a href="/jupyverse">Jupyverse</a>
                </body>
            </html>
            """

        @app.get("/jupyverse")
        async def get_jupyverse():
            id = uuid4().hex
            jupyverse_module_names = [ep.name for ep in entry_points(group="jupyverse.modules")]
            jupyverse_modules = {module_name: {"type": module_name} for module_name in jupyverse_module_names}
            jupyverse_modules["frontend"]["config"] = {"base_url": f"/jupyter/{id}/"}
            config = {
                "jupyverse": {
                    "type": "jupyverse_api.main:JupyverseModule",
                    "modules": jupyverse_modules,
                    "config": {"start_server": False},
                }
            }
            jupyverse_module = get_root_module(config)
            stop_event = Event()
            await tg.start(self._run, jupyverse_module, stop_event)
            self.jupyverses.append(stop_event)
            app.mount(f"/jupyter/{id}", jupyverse_module.app)
            url = f"/jupyter/{id}"
            response = RedirectResponse(url=url)
            return response

    async def _run(self, jupyverse_module, stop_event, *, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
        async with jupyverse_module:
            task_status.started()
            await stop_event.wait()
