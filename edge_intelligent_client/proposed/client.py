from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import List

from core.cache_manager import CacheManager, Operation
from core.client_base import ClientBase, OperationPayload
from core.decision_engine import (
    Action,
    DecisionContext,
    RuleBasedDecisionEngine,
)
from core.metrics import Metrics
from core.network_simulator import NetworkSimulator, NetworkState
from core.sync_manager import SyncManager


@dataclass
class PendingSend:
    operation: Operation
    attempts: int = 0


class ProposedClient(ClientBase):
    """
    Edge-intelligent client:
    - Monitors network via NetworkSimulator.
    - Uses decision engine to choose EXECUTE / DELAY / CACHE.
    - Maintains local persistent-like queue.
    - Syncs in order and avoids duplicates on recovery.
    """

    def __init__(
        self,
        simulator: NetworkSimulator,
        decision_engine: RuleBasedDecisionEngine | None = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.simulator = simulator
        self.decision_engine = decision_engine or RuleBasedDecisionEngine()
        self.cache_manager = CacheManager()
        self.sync_manager = SyncManager()
        self.max_retries = max_retries
        self._rng = random.Random(456)

        self._delayed: List[Operation] = []
        self._last_reconnect_time: float | None = None

    def _observe_network(self) -> NetworkState:
        return self.simulator.next_state()

    def _send_over_network(self, op: Operation, state: NetworkState) -> bool:
        if state.is_disconnected:
            return False
        fail_prob = state.packet_loss
        return self._rng.random() > fail_prob

    def handle_operation(self, op: OperationPayload) -> None:
        state = self._observe_network()
        ctx = DecisionContext(
            network_state=state,
            is_critical=op.is_critical,
            is_time_sensitive=op.is_time_sensitive,
        )
        action = self.decision_engine.decide(ctx)

        if action == Action.CACHE:
            self.cache_manager.add(
                payload=op.payload,
                is_critical=op.is_critical,
                is_time_sensitive=op.is_time_sensitive,
            )
        elif action == Action.DELAY:
            cached = self.cache_manager.add(
                payload=op.payload,
                is_critical=op.is_critical,
                is_time_sensitive=op.is_time_sensitive,
            )
            self._delayed.append(cached)
        else:  # EXECUTE
            self._attempt_send_single(op_payload=op, state=state)

    def _attempt_send_single(
        self,
        op_payload: OperationPayload,
        state: NetworkState | None = None,
    ) -> None:
        state = state or self._observe_network()
        success = self._rng.random() > state.packet_loss if not state.is_disconnected else False
        retries = 0

        while not success and retries < self.max_retries:
            retries += 1
            self.metrics.retries += 1
            state = self._observe_network()
            success = self._rng.random() > state.packet_loss if not state.is_disconnected else False

        latency_ms = state.latency_ms if not state.is_disconnected else 0.0
        bandwidth_kb = state.bandwidth_kbps / 8.0

        if success:
            self.metrics.record_success(latency_ms, bandwidth_kb, is_critical=op_payload.is_critical)
        else:
            self.metrics.record_failure(is_critical=op_payload.is_critical)
            self.metrics.data_loss += 1

    def _sync_cache_if_possible(self) -> None:
        state = self._observe_network()
        if state.is_disconnected:
            return

        ops = self.cache_manager.pop_all()
        if not ops:
            return

        to_send = self.sync_manager.sync(ops)
        if not to_send:
            return

        start = time.time()

        for op in to_send:
            success = self._send_over_network(op, state)
            retries = 0
            while not success and retries < self.max_retries:
                retries += 1
                self.metrics.retries += 1
                state = self._observe_network()
                success = self._send_over_network(op, state)

            latency_ms = state.latency_ms if not state.is_disconnected else 0.0
            bandwidth_kb = state.bandwidth_kbps / 8.0

            if success:
                self.metrics.record_success(latency_ms, bandwidth_kb, is_critical=op.is_critical)
            else:
                self.metrics.record_failure(is_critical=op.is_critical)
                self.metrics.data_loss += 1

        end = time.time()
        self.metrics.recovery_time_ms += (end - start) * 1000.0

    def tick(self) -> None:
        self._sync_cache_if_possible()
