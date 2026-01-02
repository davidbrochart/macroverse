from typing import Any
from uuid import uuid4

from anyio import Path
from anyio.abc import Process
from pydantic import BaseModel, Field, UUID4


class Environment(BaseModel):
    id: UUID4 | str = Field(default_factory=uuid4)
    path: Path | None = None
    definition: dict[str, Any] | None = None
    port: int | None = None
    process: Process | None = None
    create_time: int | None = None

    class Config:
        arbitrary_types_allowed = True
