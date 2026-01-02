import yaml
from anyio import NamedTemporaryFile, Path, run_process

from .base import Container as _Container
from ..models import Environment


class Container(_Container):
    @classmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container":
        environment = Environment(path=env_path)
        return cls(environment)

    @classmethod
    def new(cls, environment: Environment) -> "Container":
        return cls(environment)

    async def create_environment(self) -> None:
        environment_str = yaml.dump(self.environment.definition, Dumper=yaml.CDumper)
        async with NamedTemporaryFile(
            mode="wb", buffering=0, suffix=".yaml"
        ) as environment_file:
            await environment_file.write(environment_str.encode())
            create_environment_cmd = f"micromamba create -f {environment_file.name} -p {self.environment.path} --yes"
            await run_process(create_environment_cmd)

    def get_server_command(self, port: int) -> str:
        launch_jupyverse_cmd = f"jupyverse --port {port} --set frontend.base_url=/jupyverse/{self.environment.id}/"
        env_path = self.environment.path
        assert env_path is not None
        cmd = (
            """bash -c 'eval "$(micromamba shell hook --shell bash)";"""
            + f"micromamba activate environments/{env_path.name};"
            + f"{launch_jupyverse_cmd}'"
        )
        return cmd
