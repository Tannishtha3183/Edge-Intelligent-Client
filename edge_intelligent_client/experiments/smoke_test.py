from __future__ import annotations

from core.network_simulator import default_scenario_config, NetworkSimulator
from core.client_base import OperationPayload
from baseline.client import BaselineClient
from proposed.client import ProposedClient


def run_smoke():
    num_ops = 100

    cfg = default_scenario_config("intermittent")
    sim_baseline = NetworkSimulator(cfg, seed=1)
    sim_proposed = NetworkSimulator(cfg, seed=1)

    baseline = BaselineClient(simulator=sim_baseline)
    proposed = ProposedClient(simulator=sim_proposed)

    op = OperationPayload(
        payload={"example": "data"},
        is_critical=True,
        is_time_sensitive=True,
    )

    for _ in range(num_ops):
        baseline.handle_operation(op)
        proposed.handle_operation(op)

    print("Baseline metrics:")
    print(baseline.metrics)
    print("Proposed metrics:")
    print(proposed.metrics)


if __name__ == "__main__":
    run_smoke()
