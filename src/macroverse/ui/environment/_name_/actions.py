from fps import get_nowait
from holm import action
from htmy import Component

from ....hub import Hub
from ...html import get_environment, get_environments


@action.get()
async def status(name: str) -> Component:
    return get_environment(name)


@action.delete()
async def delete_environment(name: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.delete_environment(name)
        return get_environments()
