"""Tests for time manager module."""

import pytest

from .time_manager import TimeManager


class TestTimeManager:
    """Test cases for TimeManager class."""

    def test_init_with_default_values(self) -> None:
        """Should initialize with default time step and zero time."""
        time_manager = TimeManager()

        assert time_manager.time_step == 1.0
        assert time_manager.current_time == 0.0
        assert time_manager.start_time == 0.0

    def test_init_with_custom_time_step(self) -> None:
        """Should initialize with custom time step."""
        custom_step = 0.5
        time_manager = TimeManager(time_step=custom_step)

        assert time_manager.time_step == custom_step
        assert time_manager.current_time == 0.0
        assert time_manager.start_time == 0.0

    def test_set_current_time(self) -> None:
        """Should set current time to specified value."""
        time_manager = TimeManager()
        new_time = 42.5

        time_manager.set_current_time(new_time)

        assert time_manager.current_time == new_time

    def test_get_current_time(self) -> None:
        """Should return current simulation time."""
        time_manager = TimeManager()
        test_time = 15.75

        time_manager.set_current_time(test_time)

        assert time_manager.get_current_time() == test_time

    def test_advance_time_with_default_delta(self) -> None:
        """Should advance time by time_step when no delta provided."""
        time_step = 2.0
        time_manager = TimeManager(time_step=time_step)
        initial_time = 10.0
        time_manager.set_current_time(initial_time)

        time_manager.advance_time()

        assert time_manager.current_time == initial_time + time_step

    def test_advance_time_with_custom_delta(self) -> None:
        """Should advance time by specified delta."""
        time_manager = TimeManager()
        initial_time = 5.0
        delta = 3.5
        time_manager.set_current_time(initial_time)

        time_manager.advance_time(delta)

        assert time_manager.current_time == initial_time + delta

    def test_advance_time_multiple_times(self) -> None:
        """Should correctly accumulate time advances."""
        time_manager = TimeManager(time_step=1.0)

        time_manager.advance_time()  # +1.0
        time_manager.advance_time(2.5)  # +2.5
        time_manager.advance_time()  # +1.0

        assert time_manager.current_time == 4.5

    def test_reset_time(self) -> None:
        """Should reset current time to start time."""
        time_manager = TimeManager()
        time_manager.set_current_time(100.0)

        time_manager.reset()

        assert time_manager.current_time == time_manager.start_time

    def test_reset_time_with_custom_start_time(self) -> None:
        """Should reset current time to start time when start time is modified."""
        time_manager = TimeManager()
        custom_start = 10.0
        time_manager.start_time = custom_start
        time_manager.set_current_time(50.0)

        time_manager.reset()

        assert time_manager.current_time == custom_start

    def test_get_elapsed_time_from_start(self) -> None:
        """Should return elapsed time since simulation start."""
        time_manager = TimeManager()
        current_time = 25.0
        time_manager.set_current_time(current_time)

        elapsed = time_manager.get_elapsed_time()

        assert elapsed == current_time - time_manager.start_time

    def test_get_elapsed_time_with_custom_start(self) -> None:
        """Should return elapsed time relative to custom start time."""
        time_manager = TimeManager()
        start_time = 5.0
        current_time = 20.0
        time_manager.start_time = start_time
        time_manager.set_current_time(current_time)

        elapsed = time_manager.get_elapsed_time()

        assert elapsed == current_time - start_time

    def test_set_time_step_valid_value(self) -> None:
        """Should set time step to valid positive value."""
        time_manager = TimeManager()
        new_step = 0.1

        time_manager.set_time_step(new_step)

        assert time_manager.time_step == new_step

    def test_set_time_step_zero_raises_error(self) -> None:
        """Should raise ValueError when setting time step to zero."""
        time_manager = TimeManager()

        with pytest.raises(ValueError, match="Time step must be positive"):
            time_manager.set_time_step(0)

    def test_set_time_step_negative_raises_error(self) -> None:
        """Should raise ValueError when setting negative time step."""
        time_manager = TimeManager()

        with pytest.raises(ValueError, match="Time step must be positive"):
            time_manager.set_time_step(-1.0)

    def test_get_time_step(self) -> None:
        """Should return current time step value."""
        initial_step = 2.5
        time_manager = TimeManager(time_step=initial_step)

        assert time_manager.get_time_step() == initial_step

        new_step = 0.25
        time_manager.set_time_step(new_step)

        assert time_manager.get_time_step() == new_step

    def test_time_operations_integration(self) -> None:
        """Should handle complex time operations correctly."""
        time_manager = TimeManager(time_step=1.0)

        # Advance time several times
        time_manager.advance_time(5.0)  # t = 5.0
        time_manager.advance_time()  # t = 6.0
        time_manager.advance_time(2.5)  # t = 8.5

        assert time_manager.get_current_time() == 8.5
        assert time_manager.get_elapsed_time() == 8.5

        # Change time step and continue
        time_manager.set_time_step(0.5)
        time_manager.advance_time()  # t = 9.0

        assert time_manager.get_current_time() == 9.0

        # Reset and verify
        time_manager.reset()
        assert time_manager.get_current_time() == 0.0
        assert time_manager.get_elapsed_time() == 0.0
