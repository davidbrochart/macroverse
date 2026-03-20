from fps import get_nowait
from htmy import ComponentType, SafeStr, html

from ..htmui.basecoat.tabs import tab_button, tab_panel, tabs
from ..hub import Hub

cloud_icon = html.div(
    SafeStr("""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" /></svg>"""),
    class_="""mb-2 bg-muted text-foreground flex size-12 shrink-0 items-center justify-center rounded-lg [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-6"""
)


def get_servers_and_environments() -> ComponentType:
    panel_1_id = "servers-panel"
    button_1_id = f"{panel_1_id}-button"
    panel_2_id = "environments-panel"
    button_2_id = f"{panel_2_id}-button"
    return html.div(
        tabs(
            tab_panel(
                html.div(
                    get_servers(),
                    class_="card",
                ),
                id=panel_1_id,
                button_id=button_1_id,
                selected=True,
            ),
            tab_panel(
                html.div(
                    get_environments(),
                    id="environments-new",
                    class_="card",
                ),
                id=panel_2_id,
                button_id=button_2_id,
            ),
            buttons=(
                tab_button(
                    "Servers",
                    id=button_1_id,
                    panel_id=panel_1_id,
                    selected=True,
                ),
                tab_button(
                    "Environments",
                    id=button_2_id,
                    panel_id=panel_2_id,
                ),
            ),
        ),
        id="servers-and-environments",
    )


def get_servers() -> ComponentType:
    with get_nowait(Hub) as hub:
        servers = [get_server(uuid) for uuid in hub.servers]

    if servers:
        return html.div(
            html.table(
                html.tbody(*servers),
                class_="table",
            ),
            create_server(),
            id="servers",
            class_="flex max-w-sm flex-col items-center gap-3 text-center",
        )

    return html.div(
        cloud_icon,
        html.h3(
            "No Servers Yet",
            class_="text-lg font-semibold tracking-tight",
        ),
        html.p(
            "Create a server with environments.",
            class_="text-muted-foreground text-sm/relaxed",
        ),
        create_server(),
        class_="flex max-w-sm flex-col items-center gap-3 text-center",
        id="servers",
    )


def add_environment_button(id: str) -> ComponentType:
    return html.button(
        "Edit Environments",
        hx_get=f"/macroverse/server/{id}/edit-environments",
        hx_swap="outerHTML",
        id=f"server-{id}-add-enviromnent",
        class_="btn w-40",
    )


def get_server(uuid: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        server = hub.servers[uuid]
        elements = [
            html.td(
                html.a(
                    server.id[:8],
                    SafeStr("""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 7h10v10" /><path d="M7 17 17 7" /></svg>"""),
                    target="_blank",
                    rel="noopener noreferrer",
                    href=f"/jupyverse/{server.id}/?token={hub.auth_token}&redirect=/jupyverse/{server.id}/lab",
                    class_="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive underline-offset-4 hover:underline h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5 text-muted-foreground",
                )
            ),
            html.td(
                add_environment_button(uuid),
            ),
            html.td(
                html.button(
                    "Delete",
                    hx_delete=f"/macroverse/server/{server.id}",
                    hx_swap="outerHTML",
                    hx_target="#servers",
                    class_="btn-destructive",
                )
            ),
        ]
        return html.tr(
            *elements,
            id=f"server-{server.id}",
        )


def get_environments() -> ComponentType:
    with get_nowait(Hub) as hub:
        elements = [get_environment(name) for name in hub.containers]

    if elements:
        return html.div(
            html.table(
                html.tbody(*elements),
                class_="table",
            ),
            create_environment(),
            id="environments",
            class_="flex max-w-sm flex-col items-center gap-3 text-center",
        )

    return html.div(
        cloud_icon,
        html.h3(
            "No Environments Yet",
            class_="text-lg font-semibold tracking-tight",
        ),
        html.p(
            "Create an environment with packages.",
            class_="text-muted-foreground text-sm/relaxed",
        ),
        create_environment(),
        class_="flex max-w-sm flex-col items-center gap-3 text-center",
        id="environments",
    )


def get_environment(name: str) -> ComponentType:
    with get_nowait(Hub) as hub:
        container = hub.containers[name]
        elements = [html.td(name)]
        if container.create_time is None:
            _elements = [
                html.button(
                    "Delete",
                    hx_delete=f"/macroverse/environment/{name}/delete-environment",
                    hx_swap="outerHTML",
                    hx_target="#environments",
                    class_="btn-destructive",
                ),
            ]
        else:
            _elements = [creating_environment(name)]
        elements += [html.td(el) for el in _elements]
        return html.tr(
            *elements,
            id=f"environment-{name}",
        )


def start_server_button(name: str) -> ComponentType:
    return html.button(
        "Start server",
        hx_put=f"/macroverse/environment/{name}/create",
        hx_swap="outerHTML",
        hx_target=f"#environment-{name}",
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
                hx_target=f"#environment-{name}",
            )


def create_environment() -> ComponentType:
    return html.button(
        "Create Environment",
        hx_swap="outerHTML",
        hx_get="/macroverse/environment/edit-new",
        class_="btn w-80",
    )


def create_server() -> ComponentType:
    return html.button(
        "Create Server",
        hx_swap="outerHTML",
        hx_put="/macroverse/create-server",
        hx_target="#servers",
        class_="btn w-80",
    )
