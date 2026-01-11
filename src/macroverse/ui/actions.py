from fps import get_nowait
from holm import action
from htmy import Component

from .html import get_environments, get_servers
from ..hub import Hub


@action.get()
async def servers() -> Component:
    return get_servers()


@action.put()
async def create_server() -> Component:
    with get_nowait(Hub) as hub:
        await hub.create_server()
        return get_servers()


@action.get()
async def environments() -> Component:
    return get_environments()
