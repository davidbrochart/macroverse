from fps import get_nowait
from htmy import Component
from holm import action


from ...html import get_environment, get_servers_and_environments
from ....hub import Hub


@action.get()
async def status(name: str) -> Component:
    return get_environment(name)


@action.delete()
async def delete_environment(name: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.delete_environment(name)
        return get_servers_and_environments()
