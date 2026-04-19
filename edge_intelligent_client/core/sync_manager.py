from __future__ import annotations
from typing import List

from core.cache_manager import Operation

class SyncManager:
    def __init__(self):
        self._sent_ids: set[str] = set()

    def sync(self, operations: List[Operation]) -> List[Operation]:
        # Placeholder: ensure ordering & deduplication
        to_send: List[Operation] = []
        for op in sorted(operations, key=lambda o: o.timestamp):
            if op.id in self._sent_ids:
                continue
            self._sent_ids.add(op.id)
            to_send.append(op)
        return to_send
