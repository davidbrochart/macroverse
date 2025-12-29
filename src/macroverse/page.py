from htmy import Component, html

from .html import get_environments_and_create_button


def page() -> Component:
    return html.div(
        html.button(
            "Refresh",
            hx_swap="outerHTML",
            hx_get="/macroverse/environments",
            hx_target="#environments",
        ),
        get_environments_and_create_button(),
    )
