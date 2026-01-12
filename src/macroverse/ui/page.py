from htmy import Component

from .html import get_servers_and_environments


def page() -> Component:
    return get_servers_and_environments()
