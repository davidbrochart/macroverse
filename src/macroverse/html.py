from fps import get_nowait
from htmy import ComponentType, html

from .hub import Hub


def get_environments() -> ComponentType:
    with get_nowait(Hub) as hub:
        return html.table(
            html.tbody(*[get_environment(name) for name in hub.environments]),
            id="environments",
        )


def get_environment(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        environment = hub.environments[name]
        if environment.create_time is None:
            if environment.process:
                button = stop_server_button(name)
            else:
                button = start_server_button(name)
        else:
            button = creating_button(name)
        return html.tr(
            html.td(
                name
                if environment.create_time is not None or environment.process is None
                else html.a(
                    name,
                    target="_blank",
                    rel="noopener noreferrer",
                    href=f"/jupyverse/{environment.id}",
                )
            ),
            html.td(button),
            id=f"environment_{name}",
        )


def start_server_button(name: str) -> ComponentType:
    return html.button(
        "Start server",
        hx_put=f"/macroverse/environment/{name}/create",
        hx_swap="outerHTML",
        hx_target=f"#environment_{name}",
    )


def stop_server_button(name: str) -> ComponentType:
    return html.button(
        "Stop server",
        style="background:red",
        hx_delete=f"/macroverse/environment/{name}/delete",
        hx_swap="outerHTML",
        hx_target=f"#environment_{name}",
    )


def creating_button(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        environment = hub.environments[name]
        if environment.create_time is None:
            return start_server_button(name)
        else:
            return html.div(
                f"Creating ({environment.create_time}s)",
                hx_get=f"/macroverse/environment/{name}/status",
                hx_trigger="load delay:1s",
                hx_swap="outerHTML",
            )


def create_button() -> ComponentType:
    return html.button(
        "New environment",
        hx_swap="outerHTML",
        hx_get="/macroverse/environment/edit",
    )


def get_environments_and_create_button() -> ComponentType:
    return html.div(
        get_environments(),
        create_button(),
        id="environments_and_create_button",
    )
