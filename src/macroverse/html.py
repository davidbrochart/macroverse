from fps import get_nowait
from htmy import Component, Context, html

from .hub import Hub


def get_environments() -> Component:
    with get_nowait(Hub) as hub:
        return html.table(
            html.tbody(*[get_environment(name) for name in hub.environments]),
            id="environments",
        )


def get_environment(name: str) -> Component:
    with get_nowait(Hub) as hub:
        environment = hub.environments[name]
        start_server = environment.process is None
        return html.tr(
            html.td(
                html.a(
                    name,
                    target="_blank",
                    rel="noopener noreferrer",
                    href=f"/jupyverse/init/{environment.id}",
                )
                if not start_server
                else name,
            ),
            html.td(
                start_server_button(name) if start_server else stop_server_button(name),
            ),
            id=f"environment_{name}" if start_server else f"environment_{name}",
        )


def start_server_button(name: str) -> Component:
    return html.button(
        "Start server",
        hx_put=f"/macroverse/environment/{name}/create",
        hx_swap="outerHTML",
        hx_target=f"#environment_{name}",
    )


def stop_server_button(name: str) -> Component:
    return html.button(
        "Stop server",
        style="background:red",
        hx_delete=f"/macroverse/environment/{name}/delete",
        hx_swap="outerHTML",
        hx_target=f"#environment_{name}",
    )


def create_button() -> Component:
    return html.button(
        "New environment",
        hx_swap="outerHTML",
        hx_get="/macroverse/environment/edit",
    )


def get_environments_and_create_button() -> Component:
    return html.div(
        get_environments(),
        create_button(),
        id="environments_and_create_button",
    )
