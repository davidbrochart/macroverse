from typing import Annotated

from fastapi import Form
from fps import get_nowait
from holm import action
from htmy import Component, html

from ..html import get_environments, new_environment
from ...hub import Hub


@action.get()
async def edit() -> Component:
    return html.form(
        html.div(
            html.label("Environment YAML"),
            html.textarea(
                DEFAULT_ENVIRONMENT_YAML,
                name="environment_yaml",
                cols="64",
                rows="6",
            ),
        ),
        html.button(
            "Submit",
        ),
        html.button(
            "Cancel",
            hx_get="/macroverse/environment/new",
            hx_target="#edit-environment",
            hx_swap="outerHTML",
        ),
        hx_put="/macroverse/environment/create",
        hx_target="#environments-new",
        id="edit-environment",
    )


@action.get()
async def new() -> Component:
    return new_environment()


@action.put()
async def create(environment_yaml: Annotated[str, Form()]) -> Component:
    with get_nowait(Hub) as hub:
        await hub.create_environment(environment_yaml)
        return get_environments(), new_environment()


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
