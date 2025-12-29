from holm import action
from htmy import Component, html

from .html import get_environments


@action.get()
def environments() -> Component:
    return get_environments()
