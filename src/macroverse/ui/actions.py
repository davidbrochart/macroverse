from holm import action
from htmy import Component

from .html import get_environments


@action.get()
async def environments() -> Component:
    return get_environments()
