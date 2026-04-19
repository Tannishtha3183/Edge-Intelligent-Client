from __future__ import annotations

import os
from dataclasses import asdict
from typing import Dict, Any, List

import pandas as pd  # type: ignore

from core.client_base import OperationPayload
from core.network_simulator import default_scenario_config, NetworkSimulator
from baseline.client import BaselineClient
from proposed.client import ProposedClient
from proposed.client_no_cache import ProposedNoCacheClient

from experiments.workload import generate_workload


SCENARIOS = [
    "stable",
    "high_latency",
    "intermittent",
    "complete_drop",
    "mobile_fluctuation",
]

RUNS_PER_SCENARIO = 5  # multi-run experiments


def run_single_experiment(
    scenario_name: str,
    num_ops: int = 1000,
    seed: int = 1234,
) -> Dict[str, Any]:
    cfg = default_scenario_config(scenario_name)

    sim_baseline = NetworkSimulator(cfg, seed=seed)
    sim_no_cache = NetworkSimulator(cfg, seed=seed + 500)
    sim_proposed = NetworkSimulator(cfg, seed=seed + 1000)


    baseline = BaselineClient(simulator=sim_baseline)
    proposed_no_cache = ProposedNoCacheClient(simulator=sim_no_cache)
    proposed = ProposedClient(simulator=sim_proposed)

    workload = generate_workload(num_ops=num_ops, seed=seed, scenario=scenario_name)


    for op_json in workload:
        op = OperationPayload.from_json(op_json)
        baseline.handle_operation(op)
        proposed_no_cache.handle_operation(op)
        proposed.handle_operation(op)
        baseline.tick()
        proposed_no_cache.tick()
        proposed.tick()


    return {
        "scenario": scenario_name,
        "baseline": baseline.metrics,
        "proposed_no_cache": proposed_no_cache.metrics,
        "proposed": proposed.metrics,
    }



def main() -> None:
    os.makedirs("results", exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for scenario in SCENARIOS:
        for run_id in range(RUNS_PER_SCENARIO):
            seed = 1234 + run_id
            result = run_single_experiment(scenario_name=scenario, seed=seed)
            for version in ["baseline", "proposed_no_cache", "proposed"]:
                m = result[version]
                row = {
                    "scenario": scenario,
                    "version": version,
                    "run_id": run_id,
                    **asdict(m),
                }
                rows.append(row)


    df = pd.DataFrame(rows)
    out_path = os.path.join("results", "metrics_multi.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved multi-run metrics to {out_path}")


if __name__ == "__main__":
    main()
