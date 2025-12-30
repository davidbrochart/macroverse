from cyclopts import App

from .main import ContainerType, MacroverseModule


app = App()


@app.default
def main(
    container: ContainerType = "process",
    open_browser: bool = False,
) -> None:
    """Jupyverse deployment.

    Args:
        container: The type of container to use for launching servers.
        open_browser: Whether to automatically open a browser window.
    """
    macroverse_module = MacroverseModule(container, open_browser)
    macroverse_module.run()


if __name__ == "__main__":
    app()
