from typing import Annotated

from fastapi import Form
from fps import get_nowait
from holm import action
from htmy import Component, html

from ..html import get_environments, create_environment
from ...hub import Hub


@action.get()
async def edit_new() -> Component:
    return html.form(
        html.div(
            html.label("Environment YAML", for_="yaml-textarea"),
            html.textarea(
                DEFAULT_ENVIRONMENT_YAML,
                name="environment_yaml",
                id="yaml-textarea",
            ),
            html.button(
                "Submit",
                class_="btn w-40",
            ),
            html.button(
                "Cancel",
                hx_get="/macroverse/environment/new",
                hx_target="#edit-new-environment",
                hx_swap="outerHTML",
                class_="btn-destructive w-40",
            ),
            class_="grid gap-2",
        ),
        hx_put="/macroverse/environment/create",
        hx_target="#environments-new",
        id="edit-new-environment",
        class_="form grid gap-6",
    )


@action.get()
async def new() -> Component:
    return create_environment()


@action.put()
async def create(environment_yaml: Annotated[str, Form()]) -> Component:
    with get_nowait(Hub) as hub:
        await hub.create_environment(environment_yaml)
        return get_environments()


DEFAULT_ENVIRONMENT_YAML = """name: kernels
channels:
  - conda-forge
dependencies:
  - ipykernel
  - rich-click
  - anycorn
  - jupyverse-api >=0.13.1,<0.14.0
  - fps >=0.5.8,<0.6.0
  - fps-file-watcher
  - fps-kernels
  - fps-kernel-subprocess
  - fps-noauth
  - fps-frontend"""
