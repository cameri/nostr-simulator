"""Time management for discrete event simulation."""

from __future__ import annotations


class TimeManager:
    """Manages simulation time and time-related operations."""

    def __init__(self, time_step: float = 1.0) -> None:
        """Initialize the time manager.

        Args:
            time_step: The simulation time step.
        """
        self.time_step = time_step
        self.current_time = 0.0
        self.start_time = 0.0

    def set_current_time(self, time: float) -> None:
        """Set the current simulation time.

        Args:
            time: The new current time.
        """
        self.current_time = time

    def get_current_time(self) -> float:
        """Get the current simulation time.

        Returns:
            Current simulation time.
        """
        return self.current_time

    def advance_time(self, delta: float | None = None) -> None:
        """Advance simulation time by a delta.

        Args:
            delta: Time delta to advance. If None, uses time_step.
        """
        if delta is None:
            delta = self.time_step
        self.current_time += delta

    def reset(self) -> None:
        """Reset simulation time to start."""
        self.current_time = self.start_time

    def get_elapsed_time(self) -> float:
        """Get elapsed time since simulation start.

        Returns:
            Elapsed simulation time.
        """
        return self.current_time - self.start_time

    def set_time_step(self, time_step: float) -> None:
        """Set the simulation time step.

        Args:
            time_step: New time step value.
        """
        if time_step <= 0:
            raise ValueError("Time step must be positive")
        self.time_step = time_step

    def get_time_step(self) -> float:
        """Get the current time step.

        Returns:
            Current time step.
        """
        return self.time_step
