from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Scenario(str, Enum):
    STABLE = "stable"
    HIGH_LATENCY = "high_latency"
    INTERMITTENT = "intermittent"
    COMPLETE_DROP = "complete_drop"
    MOBILE_FLUCTUATION = "mobile_fluctuation"


@dataclass
class NetworkState:
    latency_ms: float
    packet_loss: float           # 0.0–1.0
    is_disconnected: bool
    bandwidth_kbps: float
    quality_score: float         # 0.0–1.0


@dataclass
class ScenarioConfig:
    scenario: Scenario
    base_latency_ms: float
    jitter_ms: float
    base_packet_loss: float
    disconnection_prob: float
    min_bandwidth_kbps: float
    max_bandwidth_kbps: float


class NetworkSimulator:
    def __init__(
        self,
        config: ScenarioConfig,
        seed: int = 42,
    ) -> None:
        self.config = config
        self._rng = random.Random(seed)
        self._step = 0

    def _sample_latency(self) -> float:
        base = self.config.base_latency_ms
        jitter = self.config.jitter_ms
        return max(0.0, self._rng.gauss(base, jitter))

    def _sample_packet_loss(self) -> float:
        base = self.config.base_packet_loss
        noise = self._rng.uniform(-0.02, 0.02)
        val = max(0.0, min(1.0, base + noise))
        return val

    def _sample_bandwidth(self) -> float:
        lo = self.config.min_bandwidth_kbps
        hi = self.config.max_bandwidth_kbps
        return self._rng.uniform(lo, hi)

    def _compute_quality_score(
        self,
        latency_ms: float,
        packet_loss: float,
        is_disconnected: bool,
        bandwidth_kbps: float,
    ) -> float:
        if is_disconnected:
            return 0.0

        # Normalize components (simple heuristic model).
        # Lower latency -> better, lower loss -> better, higher bandwidth -> better.[web:23][web:26]
        latency_score = math.exp(-latency_ms / 300.0)
        loss_score = 1.0 - packet_loss
        bw_score = min(1.0, bandwidth_kbps / max(1.0, self.config.max_bandwidth_kbps))

        raw = 0.4 * latency_score + 0.3 * loss_score + 0.3 * bw_score
        return max(0.0, min(1.0, raw))

    def next_state(self) -> NetworkState:
        self._step += 1

        is_disconnected = False

        if self.config.scenario == Scenario.COMPLETE_DROP:
            # Long full outage.
            is_disconnected = True
            latency_ms = float("inf")
            packet_loss = 1.0
            bandwidth_kbps = 0.0
        else:
            latency_ms = self._sample_latency()
            packet_loss = self._sample_packet_loss()
            bandwidth_kbps = self._sample_bandwidth()

            if self.config.scenario == Scenario.INTERMITTENT:
                # Periodic drops: every ~50 steps high chance to disconnect.
                if (self._step % 50) in (0, 1, 2, 3, 4) and self._rng.random() < 0.7:
                    is_disconnected = True
            elif self.config.scenario == Scenario.MOBILE_FLUCTUATION:
                # Fast fluctuating bandwidth & loss.[web:34][web:43]
                fluct = 0.5 * (1 + math.sin(self._step / 10.0))
                bandwidth_kbps *= (0.3 + 0.7 * fluct)
                packet_loss = max(0.0, min(1.0, packet_loss + (0.3 - fluct * 0.3)))
                if self._rng.random() < self.config.disconnection_prob * 0.5:
                    is_disconnected = True
            elif self.config.scenario == Scenario.HIGH_LATENCY:
                latency_ms *= 3.0  # stretch latency
            elif self.config.scenario == Scenario.STABLE:
                # Very low chance of random disconnect.
                if self._rng.random() < 0.01:
                    is_disconnected = True

        quality = self._compute_quality_score(
            latency_ms=latency_ms if not math.isinf(latency_ms) else 10000.0,
            packet_loss=packet_loss,
            is_disconnected=is_disconnected,
            bandwidth_kbps=bandwidth_kbps,
        )

        return NetworkState(
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            is_disconnected=is_disconnected,
            bandwidth_kbps=bandwidth_kbps,
            quality_score=quality,
        )


def default_scenario_config(name: str) -> ScenarioConfig:
    """Factory for the five required scenarios."""
    s = Scenario(name)

    if s == Scenario.STABLE:
        return ScenarioConfig(
            scenario=s,
            base_latency_ms=40.0,
            jitter_ms=5.0,
            base_packet_loss=0.01,
            disconnection_prob=0.01,
            min_bandwidth_kbps=800.0,
            max_bandwidth_kbps=1500.0,
        )
    if s == Scenario.HIGH_LATENCY:
        return ScenarioConfig(
            scenario=s,
            base_latency_ms=200.0,
            jitter_ms=50.0,
            base_packet_loss=0.05,
            disconnection_prob=0.05,
            min_bandwidth_kbps=500.0,
            max_bandwidth_kbps=1200.0,
        )
    if s == Scenario.INTERMITTENT:
        return ScenarioConfig(
            scenario=s,
            base_latency_ms=80.0,
            jitter_ms=30.0,
            base_packet_loss=0.15,
            disconnection_prob=0.2,
            min_bandwidth_kbps=200.0,
            max_bandwidth_kbps=1000.0,
        )
    if s == Scenario.COMPLETE_DROP:
        return ScenarioConfig(
            scenario=s,
            base_latency_ms=1000.0,
            jitter_ms=0.0,
            base_packet_loss=1.0,
            disconnection_prob=1.0,
            min_bandwidth_kbps=0.0,
            max_bandwidth_kbps=0.0,
        )
    if s == Scenario.MOBILE_FLUCTUATION:
        return ScenarioConfig(
            scenario=s,
            base_latency_ms=80.0,
            jitter_ms=40.0,
            base_packet_loss=0.1,
            disconnection_prob=0.15,
            min_bandwidth_kbps=100.0,
            max_bandwidth_kbps=1500.0,
        )

    raise ValueError(f"Unknown scenario: {name}")
