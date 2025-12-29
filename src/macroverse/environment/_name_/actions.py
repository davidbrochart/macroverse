from fps import get_nowait
from htmy import Component, html
from holm import action


from ...html import get_environment
from ...hub import Hub


@action.put()
async def create(name: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.start_server(name)
        return get_environment(name)


@action.delete()
async def delete(name: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.stop_server(name)
        return get_environment(name)
