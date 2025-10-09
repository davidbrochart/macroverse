from cyclopts import App

from .main import MacroverseModule


app = App()

@app.default
def main():
    macroverse_module = MacroverseModule()
    macroverse_module.run()


if __name__ == "__main__":
    app()
