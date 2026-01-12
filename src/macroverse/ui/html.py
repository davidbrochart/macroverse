from fps import get_nowait
from htmy import ComponentType, html

from ..hub import Hub


def get_servers_and_environments() -> ComponentType:
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
        id="servers-and-environments",
    )


def get_servers() -> ComponentType:
    with get_nowait(Hub) as hub:
        return html.table(
            html.tbody(*[get_server(uuid) for uuid in hub.servers]),
            id="servers",
        )


def add_environment_button(id: str) -> ComponentType:
    return html.button(
        "Add environment(s)",
        hx_get=f"/macroverse/server/{id}/edit-environments",
        hx_swap="outerHTML",
        id=f"server-{id}-add-enviromnent",
    )


def get_server(uuid: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        server = hub.servers[uuid]
        elements = [
            html.td(
                html.a(
                    server.id[:8],
                    target="_blank",
                    rel="noopener noreferrer",
                    href=f"/jupyverse/{server.id}/?token={hub.auth_token}&redirect=/jupyverse/{server.id}/lab",
                )
            ),
            html.td(
                get_server_environments(uuid),
                add_environment_button(uuid),
            ),
            html.td(
                html.button(
                    "Delete",
                    hx_delete=f"/macroverse/server/{server.id}",
                    hx_swap="outerHTML",
                    hx_target="#servers",
                    style="background:red",
                )
            ),
        ]
        return html.tr(
            *elements,
            id=f"server-{server.id}",
        )


def get_server_environments(id: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        server = hub.servers[id]
        return html.table(
            html.tbody(
                *[get_server_environment(id, name) for name in server.environments]
            ),
            id=f"server-{id}-environments",
        )


def get_server_environment(uuid: str, name: str, edit_element=None) -> ComponentType:
    elements = [
        html.td(name),
        html.td(
            html.button(
                "Remove",
                hx_delete=f"/macroverse/server/{uuid}/environment/{name}",
                hx_swap="outerHTML",
                hx_target=f"#server-{uuid}",
                style="background:red",
            ),
        ),
    ]
    if edit_element is not None:
        elements.append(html.td(edit_element))
    return html.tr(*elements)


def get_environments() -> ComponentType:
    with get_nowait(Hub) as hub:
        elements = [get_environment(name) for name in hub.containers]
        return html.table(
            html.tbody(*elements),
            id="environments",
        )


def get_environment(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        container = hub.containers[name]
        elements = [html.td(name)]
        if container.create_time is None:
            element = html.td(
                html.button(
                    "Delete",
                    hx_delete=f"/macroverse/environment/{name}/delete-environment",
                    hx_swap="outerHTML",
                    hx_target="#servers-and-environments",
                    style="background:red",
                )
            )
        else:
            element = creating_environment(name)
        elements.append(html.td(element))
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


def creating_environment(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        create_time = hub.containers[name].create_time
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


def new_environment() -> ComponentType:
    return html.button(
        "New environment",
        hx_swap="outerHTML",
        hx_get="/macroverse/environment/edit",
    )
