from htmy import Component, ComponentType, Context, component, html

from holm import Metadata


@component
def layout(children: ComponentType, context: Context) -> Component:
    metadata = Metadata.from_context(context)

    return (
        html.DOCTYPE.html,
        html.html(
            html.head(
                html.title(metadata.get("title", "Macroverse")),
                html.meta(charset="utf-8"),
                html.meta(
                    name="viewport", content="width=device-width, initial-scale=1"
                ),
                html.link(  # Use PicoCSS to add some default styling.
                    rel="stylesheet",
                    href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css",
                ),
                html.script(src="https://unpkg.com/htmx.org@4.0.0-alpha6"),
            ),
            html.body(
                html.main(children, class_="container"),
                class_="container-fluid",
            ),
        ),
    )
