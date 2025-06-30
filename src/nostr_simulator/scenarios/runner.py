"""Scenario runner script for demonstrating anti-spam strategies."""

import sys
from typing import Optional

from . import (
    run_pow_scenario,
    run_wot_scenario,
    run_multi_strategy_scenario,
    run_attack_simulation_scenario,
    run_user_behavior_scenario,
    run_strategy_comparison_scenario
)


def print_available_scenarios():
    """Print list of available scenarios."""
    scenarios = {
        "pow": "Proof of Work anti-spam strategy demonstration",
        "wot": "Web of Trust anti-spam strategy demonstration",
        "multi": "Multi-strategy anti-spam demonstration",
        "attack": "Attack simulation with various spam vectors",
        "users": "User behavior patterns and social interactions",
        "compare": "Detailed strategy comparison and analysis",
        "all": "Run all scenarios"
    }

    print("🎯 Available Scenarios:")
    print("=" * 40)
    for name, description in scenarios.items():
        print(f"  {name:<8} - {description}")
    print()


def run_scenario(scenario_name: Optional[str] = None):
    """Run a specific scenario or show available scenarios."""

    if not scenario_name or scenario_name in ["-h", "--help", "help"]:
        print_available_scenarios()
        print("Usage: python -m src.nostr_simulator.scenarios.runner <scenario_name>")
        print("   or: python -m src.nostr_simulator.scenarios.runner all")
        return

    scenario_name = scenario_name.lower()

    if scenario_name == "pow":
        run_pow_scenario()
    elif scenario_name == "wot":
        run_wot_scenario()
    elif scenario_name == "multi":
        run_multi_strategy_scenario()
    elif scenario_name == "attack":
        run_attack_simulation_scenario()
    elif scenario_name == "users":
        run_user_behavior_scenario()
    elif scenario_name == "compare":
        run_strategy_comparison_scenario()
    elif scenario_name == "all":
        print("🚀 Running all scenarios...\n")

        scenarios_to_run = [
            ("1️⃣  PoW Scenario", run_pow_scenario),
            ("2️⃣  WoT Scenario", run_wot_scenario),
            ("3️⃣  Multi-Strategy Scenario", run_multi_strategy_scenario),
            ("4️⃣  Attack Simulation Scenario", run_attack_simulation_scenario),
            ("5️⃣  User Behavior Scenario", run_user_behavior_scenario),
            ("6️⃣  Strategy Comparison Scenario", run_strategy_comparison_scenario),
        ]

        for i, (title, scenario_func) in enumerate(scenarios_to_run):
            print(title)
            print("-" * 40)
            scenario_func()

            if i < len(scenarios_to_run) - 1:  # Not the last scenario
                print("\n" + "="*60 + "\n")

        print("\n✅ All scenarios completed!")
    else:
        print(f"❌ Unknown scenario: {scenario_name}")
        print_available_scenarios()
        sys.exit(1)


if __name__ == "__main__":
    scenario_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_scenario(scenario_arg)
