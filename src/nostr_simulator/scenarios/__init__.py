"""Scenarios package for demonstrating anti-spam strategies."""

from .pow_scenario import run_pow_scenario
from .multi_strategy_scenario import run_multi_strategy_scenario
from .attack_simulation_scenario import run_attack_simulation_scenario
from .user_behavior_scenario import run_user_behavior_scenario
from .strategy_comparison_scenario import run_strategy_comparison_scenario

__all__ = [
    "run_pow_scenario",
    "run_multi_strategy_scenario",
    "run_attack_simulation_scenario",
    "run_user_behavior_scenario",
    "run_strategy_comparison_scenario"
]
