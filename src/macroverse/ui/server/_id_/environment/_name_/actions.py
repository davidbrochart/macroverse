from fps import get_nowait
from holm import action
from htmy import Component

from ......hub import Hub
from .....html import get_server


@action.delete("")
async def _(id: str, name: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.remove_server_environment(id, name)
        return get_server(id)
