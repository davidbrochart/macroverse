from typing import Annotated

from fastapi import Form
from fps import get_nowait
from holm import action
from htmy import Component, html

from ...html import add_environment_button, get_servers, get_server
from ....hub import Hub


@action.get()
async def add_environment(id: str) -> Component:
    return add_environment_button(id)


@action.delete("")
async def delete_server(id: str) -> Component:
    with get_nowait(Hub) as hub:
        await hub.stop_server(id)
        return get_servers()


@action.get()
async def edit_environments(id: str) -> Component:
    with get_nowait(Hub) as hub:
        all_environments = sorted(hub.containers)
        server = hub.servers[id]

    fields = []
    # add "" environment so that the form exists
    # but don't show that
    all_environments.append("")
    for environment_name in all_environments:
        args = dict(
            name="environment_names",
            value=environment_name,
        )
        if not environment_name:
            args["type"] = "hidden"
        else:
            args["type"] = "checkbox"
        if environment_name in server.environments:
            args["checked"] = True
        fields.append(
            html.label(
                html.input_(**args),
                environment_name,
                class_="font-normal leading-tight",
            )
        )

    return html.form(
        html.div(
            html.header(
                html.label(
                    "Environments",
                    for_="environment_names",
                    class_="text-base leading-normal",
                ),
                html.p(
                    "Select the environments you want for this server.",
                    class_="text-muted-foreground text-sm",
                ),
            ),
            html.fieldset(
                *fields,
                id="demo-form-checkboxes",
                class_="flex flex-col gap-2",
            ),
            html.button(
                "Save",
                class_="btn w-40",
            ),
            html.button(
                "Cancel",
                hx_get=f"/macroverse/server/{id}/add-environment",
                hx_target=f"#server-{id}-add-environment",
                class_="btn-destructive w-40",
            ),
            class_="grid gap-2",
        ),
        hx_put=f"/macroverse/server/{id}/environments",
        hx_target=f"#server-{id}",
        hx_swap="outerHTML",
        id=f"server-{id}-add-environment",
        class_="form flex flex-col gap-4",
    )


@action.put()
async def environments(id: str, environment_names: Annotated[list[str], Form()]) -> Component:
    environment_names.remove("")
    with get_nowait(Hub) as hub:
        server = hub.servers[id]
        server_environments = set(server.environments)
        for name in server_environments:
            if name not in environment_names:
                await hub.remove_server_environment(id, name)
        for name in environment_names:
            if name not in server.environments:
                await hub.add_server_environment(id, name)
        return get_server(id)
