from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

from core.metrics import Metrics


@dataclass
class OperationPayload:
    payload: Dict[str, Any]
    is_critical: bool
    is_time_sensitive: bool

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "OperationPayload":
        return cls(
            payload=data.get("payload", {}),
            is_critical=bool(data.get("is_critical", False)),
            is_time_sensitive=bool(data.get("is_time_sensitive", False)),
        )


class ClientBase(ABC):
    def __init__(self) -> None:
        self.metrics = Metrics()

    @abstractmethod
    def handle_operation(self, op: OperationPayload) -> None:
        ...

    @abstractmethod
    def tick(self) -> None:
        ...
