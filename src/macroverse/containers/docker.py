import yaml
from anyio import Path, run_process

from .base import Container as _Container
from ..models import Environment


class Container(_Container):
    @classmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container":
        dockerfile = await (env_path / "Dockerfile").read_text()
        environment_id = dockerfile.splitlines()[-1][2:]
        environment = Environment(id=environment_id, path=env_path)
        return cls(environment)

    def get_server_command(self, port: int) -> str:
        launch_jupyverse_cmd = f"jupyverse --host 0.0.0.0 --port 5000 --set frontend.base_url=/jupyverse/{self.environment.id}/"
        cmd = f"docker run -p {port}:5000 {self.environment.id} {launch_jupyverse_cmd}"
        return cmd

    @classmethod
    def new(cls, environment: Environment) -> "Container":
        return cls(environment)

    async def create_environment(self) -> None:
        env_def = self.environment.definition
        assert env_def is not None
        env_def["name"] = "base"
        environment_str = yaml.dump(self.environment.definition, Dumper=yaml.CDumper)
        env_path = self.environment.path
        assert env_path is not None
        await env_path.mkdir(parents=True)
        await (env_path / "environment.yaml").write_text(environment_str)
        dockerfile_str = DOCKERFILE.replace("ENVIRONMENT_ID", str(self.environment.id))
        await (env_path / "Dockerfile").write_text(dockerfile_str)
        build_docker_image_cmd = (
            f"docker build --tag {self.environment.id} {self.environment.path}"
        )
        await run_process(build_docker_image_cmd, stdout=None, stderr=None)


DOCKERFILE = """\
FROM mambaorg/micromamba:2.4.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yaml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml &&  micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1
EXPOSE 5000
# ENVIRONMENT_ID
"""
