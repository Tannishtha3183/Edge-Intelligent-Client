from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from core.client_base import ClientBase, OperationPayload
from core.decision_engine import (
    Action,
    DecisionContext,
    RuleBasedDecisionEngine,
)
from core.metrics import Metrics
from core.network_simulator import NetworkSimulator, NetworkState


@dataclass
class PendingOp:
    op: OperationPayload
    attempts: int = 0


class ProposedNoCacheClient(ClientBase):
    """
    Ablation client:
    - Uses decision engine but does NOT use persistent cache or sync.
    - DELAY = retry later in-place, but if it fails while disconnected, op is lost.
    """

    def __init__(
        self,
        simulator: NetworkSimulator,
        decision_engine: RuleBasedDecisionEngine | None = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__()
        self.simulator = simulator
        self.decision_engine = decision_engine or RuleBasedDecisionEngine()
        self.max_retries = max_retries
        self._rng = random.Random(789)

        self._delayed: List[PendingOp] = []

    def _observe_network(self) -> NetworkState:
        return self.simulator.next_state()

    def _attempt_send(self, op: OperationPayload, state: NetworkState | None = None) -> None:
        state = state or self._observe_network()
        success = (not state.is_disconnected) and (self._rng.random() > state.packet_loss)
        retries = 0

        while not success and retries < self.max_retries:
            retries += 1
            self.metrics.retries += 1
            state = self._observe_network()
            success = (not state.is_disconnected) and (self._rng.random() > state.packet_loss)

        latency_ms = state.latency_ms if not state.is_disconnected else 0.0
        bandwidth_kb = state.bandwidth_kbps / 8.0

        if success:
            self.metrics.record_success(latency_ms, bandwidth_kb)
        else:
            self.metrics.record_failure()
            self.metrics.data_loss += 1

    def handle_operation(self, op: OperationPayload) -> None:
        state = self._observe_network()
        ctx = DecisionContext(
            network_state=state,
            is_critical=op.is_critical,
            is_time_sensitive=op.is_time_sensitive,
        )
        action = self.decision_engine.decide(ctx)

        if action == Action.CACHE:
            # In this ablation, CACHE behaves like DELAY without persistence.
            self._delayed.append(PendingOp(op=op))
        elif action == Action.DELAY:
            self._delayed.append(PendingOp(op=op))
        else:
            self._attempt_send(op, state=state)

    def tick(self) -> None:
        # Try sending delayed operations when network improves.
        if not self._delayed:
            return

        state = self._observe_network()
        if state.is_disconnected:
            return

        remaining: List[PendingOp] = []
        for pending in self._delayed:
            self._attempt_send(pending.op, state=state)
            # No true persistence: if it failed again, we simply drop it.
        self._delayed = remaining
