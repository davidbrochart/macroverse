from fps import get_nowait
from htmy import Component, ComponentType
from holm import action


from ...html import creating_button, get_environment
from ...hub import Hub


@action.get()
async def status(name: str) -> ComponentType:
    return creating_button(name)


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
