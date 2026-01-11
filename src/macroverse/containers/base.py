from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from anyio import Path
from anyio.abc import Process


@dataclass
class Container(ABC):
    id: UUID | str = field(default_factory=uuid4)
    path: Path | None = None
    definition: dict[str, Any] | None = None
    port: int | None = None
    process: Process | None = None
    create_time: int | None = None
    nginx_conf: str | None = None
    routes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    @abstractmethod
    async def from_existing_environment(cls, env_path: Path) -> "Container": ...

    @abstractmethod
    async def create_environment(self) -> None: ...

    @abstractmethod
    def get_server_command(self, port: int) -> str: ...
