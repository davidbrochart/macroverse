from cyclopts import App

from .main import MacroverseModule


app = App()


@app.default
def main(
    open_browser: bool = True,
) -> None:
    """Jupyverse deployment.

    Args:
        open_browser: Whether to automatically open a browser window.
    """
    macroverse_module = MacroverseModule(open_browser)
    macroverse_module.run()


if __name__ == "__main__":
    app()
