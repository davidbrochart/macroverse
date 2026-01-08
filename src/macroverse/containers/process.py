from anyio import NamedTemporaryFile, Path, run_process
from yaml import dump

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from .base import Container as _Container


class Container(_Container):
    @classmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container":
        return cls(path=env_path)

    async def create_environment(self) -> None:
        environment_str = dump(self.definition, Dumper=Dumper)
        async with NamedTemporaryFile(
            mode="wb", buffering=0, suffix=".yaml"
        ) as environment_file:
            await environment_file.write(environment_str.encode())
            create_environment_cmd = (
                f"micromamba create -f {environment_file.name} -p {self.path} --yes"
            )
            await run_process(create_environment_cmd)

    def get_server_command(self, port: int) -> str:
        launch_jupyverse_cmd = f'jupyverse --port {port} --set frontend.base_url=/jupyverse/{self.id}/ --set openapi_url="" --set routes_url="/routes" --timeout 10'
        assert self.path is not None
        cmd = (
            """bash -c 'eval "$(micromamba shell hook --shell bash)";"""
            + f"micromamba activate environments/{self.path.name};"
            + f"{launch_jupyverse_cmd}'"
        )
        return cmd
