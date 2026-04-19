from __future__ import annotations

import random
from typing import Dict, Any, List

from core.network_simulator import Scenario  # if needed

def generate_workload(num_ops: int = 1000, seed: int = 1234, scenario: str | None = None) -> List[Dict[str, Any]]:
    rng = random.Random(seed)

    # default mix
    if scenario is None:
        critical_prob = 0.2
        time_sensitive_prob = 0.3
    elif scenario == "intermittent" or scenario == "mobile_fluctuation":
        critical_prob = 0.4      # more critical ops in unstable networks
        time_sensitive_prob = 0.5
    else:
        critical_prob = 0.2
        time_sensitive_prob = 0.3

    workload: List[Dict[str, Any]] = []
    for i in range(num_ops):
        is_critical = rng.random() < critical_prob
        is_time_sensitive = rng.random() < time_sensitive_prob
        payload = {
            "op_id": i,
            "value": rng.randint(1, 1000),
        }
        workload.append(
            {
                "payload": payload,
                "is_critical": is_critical,
                "is_time_sensitive": is_time_sensitive,
            }
        )
    return workload

