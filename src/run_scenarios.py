#!/usr/bin/env python3
"""Main entry point for running Nostr anti-spam scenarios."""

import sys

from nostr_simulator.scenarios.runner import run_scenario

if __name__ == "__main__":
    scenario_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_scenario(scenario_arg)
