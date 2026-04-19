from __future__ import annotations

import logging
import random

from core.client_base import ClientBase, OperationPayload
from core.metrics import Metrics
from core.network_simulator import NetworkSimulator, NetworkState


class ProposedNoCacheClient(ClientBase):
    """
    Ablation client:
    - Uses the same decision rules as baseline (send immediately, simple retries).
    - NO cache / sync layer.
    - Lets us isolate the benefit of the cache+sync in the full ProposedClient.
    """

    def __init__(self, simulator: NetworkSimulator, max_retries: int = 3) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.simulator = simulator
        self.max_retries = max_retries
        self._rng = random.Random(789)

    def _send_over_network(self, state: NetworkState) -> bool:
        if state.is_disconnected:
            return False
        fail_prob = state.packet_loss
        return self._rng.random() > fail_prob

    def handle_operation(self, op: OperationPayload) -> None:
        state = self.simulator.next_state()
        success = self._send_over_network(state)
        retries = 0

        while not success and retries < self.max_retries:
            retries += 1
            self.metrics.retries += 1
            state = self.simulator.next_state()
            success = self._send_over_network(state)

        latency_ms = state.latency_ms if not state.is_disconnected else 0.0
        bandwidth_kb = state.bandwidth_kbps / 8.0

        if success:
            self.metrics.record_success(latency_ms, bandwidth_kb, is_critical=op.is_critical)
        else:
            self.metrics.record_failure(is_critical=op.is_critical)
            self.metrics.data_loss += 1


    def tick(self) -> None:
        # No periodic cache/sync logic in this ablation client.
        return
