from fps import get_nowait
from htmy import ComponentType, html

from .hub import Hub


def get_environments() -> ComponentType:
    with get_nowait(Hub) as hub:
        return html.table(
            html.tbody(*[get_environment(name) for name in hub.containers]),
            id="environments",
        )


def get_environment(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        environment = hub.containers[name].environment
        elements = [
            html.td(
                name
                if environment.create_time is not None or environment.process is None
                else html.a(
                    name,
                    target="_blank",
                    rel="noopener noreferrer",
                    href=f"/jupyverse/{environment.id}/?token={hub.auth_token}&redirect=/jupyverse/{environment.id}/lab",
                )
            )
        ]
        add_delete_button = True
        if environment.create_time is None:
            if environment.process:
                button = stop_server_button(name)
            else:
                button = start_server_button(name)
        else:
            button = creating_button(name)
            add_delete_button = False
        elements.append(html.td(button))
        if add_delete_button:
            elements.append(
                html.td(
                    html.button(
                        "Delete environment",
                        hx_delete=f"/macroverse/environment/{name}/delete-environment",
                        hx_swap="outerHTML",
                        hx_target="#environments",
                        style="background:red",
                    )
                )
            )
        return html.tr(
            *elements,
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
        create_time = hub.containers[name].environment.create_time
        if create_time is None:
            return start_server_button(name)
        else:
            return html.div(
                f"Creating ({create_time}s)",
                hx_get=f"/macroverse/environment/{name}/status",
                hx_trigger="load delay:1s",
                hx_swap="outerHTML",
                hx_target=f"#environment_{name}",
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
