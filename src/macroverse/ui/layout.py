from holm import Metadata
from htmy import Component, ComponentType, Context, SafeStr, component, html

from ..htmui.basecoat import cdn as basecoat_cdn
from ..htmui.basecoat import init_on_htmx_history_restore as basecoat_init
from ..htmui.basecoat import theme_switcher


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
                SafeStr(  # HTMX
                    '<script src="https://cdn.jsdelivr.net/npm/htmx.org@4.0.0-alpha8/dist/htmx.min.js"></script>'
                ),
                html.link(rel="stylesheet", href="/static/basecoat.css"),
                basecoat_cdn.js,
                basecoat_init,
                theme_switcher.js,
            ),
            html.body(
                html.div(
                    html.header(
                        html.div(class_="btn-icon-ghost mr-auto"),
                        theme_switcher.theme_switcher(),
                        class_="w-full flex shrink-0 items-center p-4 gap-2 sticky top-0 z-10 "
                        "bg-background isolate border-b",
                    ),
                    html.main(
                        html.div(
                            children, class_="mx-auto w-full flex-1 max-w-screen-md"
                        ),
                        class_=(
                            "w-full max-w-screen-lg p-4 md:p-6 xl:p-12 mx-auto relative flex gap-10 grow"
                        ),
                    ),
                    class_="min-h-full flex flex-col",
                ),
                class_="h-screen v-screen",
            ),
        ),
    )
