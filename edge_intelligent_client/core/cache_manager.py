from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List
import time
import uuid

@dataclass
class Operation:
    id: str
    payload: dict
    is_critical: bool
    is_time_sensitive: bool
    timestamp: float

class CacheManager:
    def __init__(self):
        self._queue: List[Operation] = []

    def add(self, payload: dict, is_critical: bool, is_time_sensitive: bool) -> Operation:
        op = Operation(
            id=str(uuid.uuid4()),
            payload=payload,
            is_critical=is_critical,
            is_time_sensitive=is_time_sensitive,
            timestamp=time.time(),
        )
        self._queue.append(op)
        return op

    def pop_all(self) -> list[Operation]:
        ops = list(self._queue)
        self._queue.clear()
        return ops

    def size(self) -> int:
        return len(self._queue)
