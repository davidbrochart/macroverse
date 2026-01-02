from abc import ABC, abstractmethod
from dataclasses import dataclass

from anyio import Path

from ..models import Environment


@dataclass
class Container(ABC):
    environment: Environment

    @classmethod
    @abstractmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container": ...

    @classmethod
    @abstractmethod
    def new(cls, environment: Environment) -> "Container": ...

    @abstractmethod
    async def create_environment(self) -> None: ...

    @abstractmethod
    def get_server_command(self, port: int) -> str: ...
