from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Metrics:
    successes: int = 0
    failures: int = 0
    retries: int = 0
    total_ops: int = 0
    total_latency_ms: float = 0.0
    total_bandwidth_kb: float = 0.0
    data_loss: int = 0
    recovery_time_ms: float = 0.0

    # optional critical metrics (safe even if you don't use them everywhere)
    critical_successes: int = 0
    critical_data_loss: int = 0

    def record_success(self, latency_ms: float, bandwidth_kb: float, is_critical: bool = False) -> None:
        self.total_ops += 1
        self.successes += 1
        self.total_latency_ms += latency_ms
        self.total_bandwidth_kb += bandwidth_kb
        if is_critical:
            self.critical_successes += 1

    def record_failure(self, is_critical: bool = False) -> None:
        self.total_ops += 1
        self.failures += 1
        if is_critical:
            self.critical_data_loss += 1

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.successes if self.successes else 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_ops if self.total_ops else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.total_ops if self.total_ops else 0.0

    @property
    def critical_success_rate(self) -> float:
        total_critical = self.critical_successes + self.critical_data_loss
        return self.critical_successes / total_critical if total_critical else 0.0
