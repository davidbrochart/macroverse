from anyio import Path, run_process
from yaml import dump

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from .base import Container as _Container


class Container(_Container):
    @classmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container":
        dockerfile = await (env_path / "Dockerfile").read_text()
        environment_id = dockerfile.splitlines()[-1][2:]
        return cls(id=environment_id, path=env_path)

    def get_server_command(self, port: int) -> str:
        launch_jupyverse_cmd = f'jupyverse --host 0.0.0.0 --port 5000 --set frontend.base_url=/jupyverse/{self.id}/ --set openapi_url="" --set routes_url="/routes" --timeout 10'
        cmd = f"docker run -p {port}:5000 {self.id} {launch_jupyverse_cmd}"
        return cmd

    async def create_environment(self) -> None:
        assert self.definition is not None
        self.definition["name"] = "base"
        environment_str = dump(self.definition, Dumper=Dumper)
        assert self.path is not None
        await self.path.mkdir(parents=True)
        await (self.path / "environment.yaml").write_text(environment_str)
        dockerfile_str = DOCKERFILE.replace("ENVIRONMENT_ID", str(self.id))
        await (self.path / "Dockerfile").write_text(dockerfile_str)
        build_docker_image_cmd = f"docker build --tag {self.id} {self.path}"
        await run_process(build_docker_image_cmd, stdout=None, stderr=None)


DOCKERFILE = """\
FROM mambaorg/micromamba:2.4.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yaml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml &&  micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1
EXPOSE 5000
# ENVIRONMENT_ID
"""
