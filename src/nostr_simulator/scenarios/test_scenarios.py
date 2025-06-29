"""Test scenarios to ensure they run without errors."""

import io
import sys
from unittest.mock import patch

from ..scenarios import (
    run_pow_scenario,
    run_multi_strategy_scenario,
    run_attack_simulation_scenario,
    run_user_behavior_scenario,
    run_strategy_comparison_scenario
)


class TestScenarios:
    """Test scenarios to ensure they execute successfully."""

    def capture_output(self, func):
        """Capture stdout during function execution."""
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        try:
            func()
            return captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_pow_scenario_runs_successfully(self):
        """Test that PoW scenario runs without errors."""
        output = self.capture_output(run_pow_scenario)
        assert "Proof of Work Scenario" in output
        assert "Strategy metrics" in output
        assert "Scenario Summary" in output

    def test_multi_strategy_scenario_runs_successfully(self):
        """Test that multi-strategy scenario runs without errors."""
        output = self.capture_output(run_multi_strategy_scenario)
        assert "Multi-Strategy Anti-Spam Scenario" in output
        assert "HONEST user" in output
        assert "SPAMMER user" in output
        assert "Final Statistics" in output

    def test_attack_simulation_scenario_runs_successfully(self):
        """Test that attack simulation scenario runs without errors."""
        output = self.capture_output(run_attack_simulation_scenario)
        assert "Attack Simulation Scenario" in output
        assert "Sybil Attack" in output
        assert "Burst Spam Attack" in output
        assert "Overall Attack Defense Summary" in output

    def test_user_behavior_scenario_runs_successfully(self):
        """Test that user behavior scenario runs without errors."""
        output = self.capture_output(run_user_behavior_scenario)
        assert "User Behavior Scenario" in output
        assert "Creating user agents" in output
        assert "Social graph statistics" in output or "User behavior scenario completed" in output
        assert "User Behavior Summary" in output or "Key Insights" in output

    def test_strategy_comparison_scenario_runs_successfully(self):
        """Test that strategy comparison scenario runs without errors."""
        output = self.capture_output(run_strategy_comparison_scenario)
        assert "Strategy Comparison Scenario" in output
        assert "Proof of Work Strategy" in output
        assert "Rate Limiting Strategy" in output or "Rate limiting is effective" in output
        assert "Combined Strategy" in output
        assert "Strategy Comparison Summary" in output or "Scenario Summary" in output

    def test_all_scenarios_contain_expected_content(self):
        """Test that scenarios produce expected content types."""
        # Test PoW scenario
        pow_output = self.capture_output(run_pow_scenario)
        assert "Mining PoW" in pow_output
        assert "PoW found" in pow_output or "PoW mining timed out" in pow_output

        # Test multi-strategy scenario
        multi_output = self.capture_output(run_multi_strategy_scenario)
        assert "ALLOWED" in multi_output or "BLOCKED" in multi_output
        assert "Statistics" in multi_output

        # Test attack scenario
        attack_output = self.capture_output(run_attack_simulation_scenario)
        assert "Generating" in attack_output
        assert "blocked by" in attack_output

        # Test user behavior scenario
        user_behavior_output = self.capture_output(run_user_behavior_scenario)
        assert "Creating user agents" in user_behavior_output
        assert "User" in user_behavior_output

        # Test strategy comparison scenario
        strategy_comparison_output = self.capture_output(run_strategy_comparison_scenario)
        assert "Strategy" in strategy_comparison_output
        assert "events" in strategy_comparison_output or "messages" in strategy_comparison_output
