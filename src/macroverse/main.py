import webbrowser
from importlib.metadata import entry_points

from anyio import create_task_group, sleep_forever
from fps import Module
from jupyverse_api.auth import Auth
from jupyverse_api.main import QueryParams
from fastapi import FastAPI

from .routes import Macroverse


class MacroverseModule(Module):
    def __init__(self, name: str = "macroverse"):
        super().__init__(name)
        self.add_module("fps.web.fastapi:FastAPIModule", "fastapi_app")
        self.add_module("fps.web.server:ServerModule", "server", host="localhost", port=8000)

    async def prepare(self):
        app = await self.get(FastAPI)

        async with create_task_group() as tg:
            macroverse = Macroverse(app, tg)
            self.put(macroverse)

            def cb():
                for stop_event in macroverse.jupyverses:
                    stop_event.set()

            self.add_teardown_callback(cb)
            self.done()
            await sleep_forever()

    async def start(self):
        async with create_task_group() as tg:
            tg.start_soon(super().start)
            await self.modules["server"].started.wait()
            url = f"http://127.0.0.1:8000"
            webbrowser.open_new_tab(url)
