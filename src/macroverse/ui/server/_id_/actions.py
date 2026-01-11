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
    return html.form(
        html.div(
            html.label("Environment name(s)"),
            html.textarea(name="environment_names"),
        ),
        html.button(
            "Submit",
        ),
        html.button(
            "Cancel",
            hx_get=f"/macroverse/server/{id}/add-environment",
            hx_target=f"#server-{id}-add-environment",
        ),
        hx_put=f"/macroverse/server/{id}/environments",
        hx_target=f"#server-{id}",
        hx_swap="outerHTML",
        id=f"server-{id}-add-environment",
    )


@action.put()
async def environments(id: str, environment_names: Annotated[str, Form()]) -> Component:
    environment_list = environment_names.split()
    with get_nowait(Hub) as hub:
        for name in environment_list:
            await hub.add_server_environment(id, name)
        return get_server(id)
