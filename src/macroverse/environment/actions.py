from typing import Annotated

from fastapi import Form
from fps import get_nowait
from holm import action
from htmy import Component, html

from ..html import get_environments_and_create_button
from ..hub import Hub


@action.get()
async def edit() -> Component:
    return html.form(
        html.div(
            html.label("Environment YAML"),
            html.textarea(
                name="environment_yaml",
            ),
        ),
        html.button(
            "Submit",
        ),
        html.button(
            "Cancel",
            hx_get="/macroverse/environment/cancel",
        ),
        hx_put="/macroverse/environment/create",
        hx_target="#environments_and_create_button",
        hw_swap="outerHTML",
    )


@action.get()
async def cancel() -> Component:
    return get_environments_and_create_button()


@action.put()
async def create(environment_yaml: Annotated[str, Form()]) -> Component:
    with get_nowait(Hub) as hub:
        hub.create_environment(environment_yaml)
        return get_environments_and_create_button()
