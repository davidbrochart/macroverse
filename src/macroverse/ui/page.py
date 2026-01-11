from htmy import Component, html

from .html import get_environments, get_servers, new_environment


def page() -> Component:
    return html.div(
        get_servers(),
        html.button(
            "New server",
            hx_swap="outerHTML",
            hx_put="/macroverse/create-server",
            hx_target="#servers",
        ),
        html.div(
            get_environments(),
            new_environment(),
            id="environments-new",
        ),
    )
