from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from core.network_simulator import NetworkState


class Action(str, Enum):
    EXECUTE = "execute"
    DELAY = "delay"
    CACHE = "cache"


@dataclass
class DecisionContext:
    network_state: NetworkState
    is_critical: bool
    is_time_sensitive: bool


class DecisionEngine(Protocol):
    def decide(self, ctx: DecisionContext) -> Action:
        ...

    def reward(
        self,
        success: bool,
        latency_ms: float,
        retries: int,
    ) -> float:
        ...


class RuleBasedDecisionEngine:
    def __init__(
        self,
        poor_threshold: float = 0.3,
        medium_threshold: float = 0.7,
        alpha: float = 1.0,
        beta: float = 0.001,
        gamma: float = 0.1,
    ) -> None:
        self.poor_threshold = poor_threshold
        self.medium_threshold = medium_threshold
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def decide(self, ctx: DecisionContext) -> Action:
        q = ctx.network_state.quality_score
        if q <= self.poor_threshold:
            return Action.CACHE
        if q <= self.medium_threshold:
            return Action.DELAY
        return Action.EXECUTE

    def reward(
        self,
        success: bool,
        latency_ms: float,
        retries: int,
    ) -> float:
        """
        Learning-ready reward:
        r = alpha * success - beta * latency_ms - gamma * retries
        success in {0,1}.[web:26]
        """
        success_val = 1.0 if success else 0.0
        return self.alpha * success_val - self.beta * latency_ms - self.gamma * retries
