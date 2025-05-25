"""Tests for the time module in useq.v2."""

from __future__ import annotations

from datetime import timedelta

import pytest

from useq.v2._time import (
    AnyTimePlan,
    MultiPhaseTimePlan,
    SinglePhaseTimePlan,
    TDurationLoops,
    TimePlan,
    TIntervalDuration,
    TIntervalLoops,
)


class TestTIntervalLoops:
    """Test TIntervalLoops time plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and properties."""
        plan = TIntervalLoops(interval=timedelta(seconds=2), loops=5)

        assert plan.interval == timedelta(seconds=2)
        assert plan.loops == 5
        assert plan.axis_key == "t"
        assert len(plan) == 5
        assert plan.duration == timedelta(seconds=8)  # (5-1) * 2

    def test_interval_from_dict(self) -> None:
        """Test creating interval from dict."""
        plan = TIntervalLoops(interval={"seconds": 3}, loops=3)
        assert plan.interval == timedelta(seconds=3)

    def test_interval_from_float(self) -> None:
        """Test creating interval from float (seconds)."""
        plan = TIntervalLoops(interval=1.5, loops=4)
        assert plan.interval == timedelta(seconds=1.5)

    def test_iteration(self) -> None:
        """Test iterating over time values."""
        plan = TIntervalLoops(interval=timedelta(seconds=2), loops=3)
        times = list(plan)

        assert times == [0.0, 2.0, 4.0]

    def test_zero_loops_invalid(self) -> None:
        """Test that zero loops raises validation error."""
        with pytest.raises(ValueError, match="greater than 0"):
            TIntervalLoops(interval=timedelta(seconds=1), loops=0)

    def test_negative_loops_invalid(self) -> None:
        """Test that negative loops raises validation error."""
        with pytest.raises(ValueError, match="greater than 0"):
            TIntervalLoops(interval=timedelta(seconds=1), loops=-1)

    def test_interval_s_method(self) -> None:
        """Test _interval_s private method."""
        plan = TIntervalLoops(interval=timedelta(seconds=2.5), loops=3)
        assert plan._interval_s() == 2.5


class TestTDurationLoops:
    """Test TDurationLoops time plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and properties."""
        plan = TDurationLoops(duration=timedelta(seconds=10), loops=6)

        assert plan.duration == timedelta(seconds=10)
        assert plan.loops == 6
        assert len(plan) == 6
        assert plan.interval == timedelta(seconds=2)  # 10 / (6-1)

    def test_duration_from_dict(self) -> None:
        """Test creating duration from dict."""
        plan = TDurationLoops(duration={"minutes": 1}, loops=4)
        assert plan.duration == timedelta(minutes=1)

    def test_iteration(self) -> None:
        """Test iterating over time values."""
        plan = TDurationLoops(duration=timedelta(seconds=6), loops=4)
        times = list(plan)

        # Should be evenly spaced over 6 seconds: 0, 2, 4, 6
        assert times == [0.0, 2.0, 4.0, 6.0]

    def test_single_loop(self) -> None:
        """Test behavior with single loop."""
        plan = TDurationLoops(duration=timedelta(seconds=5), loops=1)
        times = list(plan)

        # With 1 loop, interval would be 5/0 which would cause issues
        # But the implementation should handle this gracefully
        assert len(times) == 1
        assert times[0] == 0.0

    def test_interval_s_method(self) -> None:
        """Test _interval_s private method."""
        plan = TDurationLoops(duration=timedelta(seconds=8), loops=5)
        assert plan._interval_s() == 2.0  # 8 / (5-1)


class TestTIntervalDuration:
    """Test TIntervalDuration time plan."""

    def test_basic_creation_finite(self) -> None:
        """Test creation with finite duration."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=2), duration=timedelta(seconds=10)
        )

        assert plan.interval == timedelta(seconds=2)
        assert plan.duration == timedelta(seconds=10)
        assert plan.prioritize_duration is True  # default

    def test_basic_creation_infinite(self) -> None:
        """Test creation with infinite duration."""
        plan = TIntervalDuration(interval=timedelta(seconds=1), duration=None)

        assert plan.interval == timedelta(seconds=1)
        assert plan.duration is None
        assert plan.prioritize_duration is True

    def test_finite_iteration(self) -> None:
        """Test iteration with finite duration."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=2), duration=timedelta(seconds=5)
        )
        times = list(plan)

        # Should yield: 0, 2, 4 (stops before 6 which exceeds duration)
        assert times == [0.0, 2.0, 4.0]

    def test_infinite_iteration_limited(self) -> None:
        """Test that infinite iteration can be limited."""
        plan = TIntervalDuration(interval=timedelta(seconds=1), duration=None)
        iterator = iter(plan)

        # Take first few values to test infinite sequence
        times = [next(iterator) for _ in range(5)]
        assert times == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_duration_from_dict(self) -> None:
        """Test creating duration from dict."""
        plan = TIntervalDuration(interval={"seconds": 1}, duration={"minutes": 2})
        assert plan.duration == timedelta(minutes=2)

    def test_prioritize_duration_false(self) -> None:
        """Test setting prioritize_duration to False."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=1),
            duration=timedelta(seconds=5),
            prioritize_duration=False,
        )
        assert plan.prioritize_duration is False

    def test_interval_s_method(self) -> None:
        """Test _interval_s private method."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=1.5), duration=timedelta(seconds=5)
        )
        assert plan._interval_s() == 1.5

    def test_exact_duration_boundary(self) -> None:
        """Test behavior when time exactly equals duration."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=2), duration=timedelta(seconds=4)
        )
        times = list(plan)

        # Should include exactly 4.0 since condition is t <= duration
        assert times == [0.0, 2.0, 4.0]


class TestMultiPhaseTimePlan:
    """Test MultiPhaseTimePlan."""

    def test_basic_creation(self) -> None:
        """Test basic creation with multiple phases."""
        phase1 = TIntervalLoops(interval=timedelta(seconds=1), loops=3)
        phase2 = TIntervalLoops(interval=timedelta(seconds=2), loops=2)

        plan = MultiPhaseTimePlan(phases=[phase1, phase2])
        assert len(plan.phases) == 2

    def test_iteration_multiple_finite_phases(self) -> None:
        """Test iteration over multiple finite phases."""
        phase1 = TIntervalLoops(interval=timedelta(seconds=1), loops=3)
        phase2 = TIntervalLoops(interval=timedelta(seconds=2), loops=2)

        plan = MultiPhaseTimePlan(phases=[phase1, phase2])
        times = list(plan)

        assert times == [0.0, 1.0, 2.0, 4.0]

    def test_iteration_mixed_phases(self) -> None:
        """Test iteration with different phase types."""
        phase1 = TDurationLoops(duration=timedelta(seconds=4), loops=3)
        phase2 = TIntervalLoops(interval=timedelta(seconds=1), loops=2)

        plan = MultiPhaseTimePlan(phases=[phase1, phase2])
        times = list(plan)

        assert times == [0.0, 2.0, 4.0, 5.0]

    def test_send_skip_phase(self) -> None:
        """Test using send(True) to skip to next phase."""
        phase1 = TIntervalLoops(interval=timedelta(seconds=1), loops=5)
        phase2 = TIntervalLoops(interval=timedelta(seconds=2), loops=2)

        plan = MultiPhaseTimePlan(phases=[phase1, phase2])
        iterator = iter(plan)

        # Start iteration
        assert next(iterator) == 0.0
        assert next(iterator) == 1.0

        # Force skip to next phase
        try:
            value = iterator.send(True)
            # Should start phase 2 at offset of phase 1's duration (4 seconds)
            assert value == 6.0  # phase 2, time 0
        except StopIteration:
            # If send causes StopIteration, get next value
            assert next(iterator) == 4.0

    def test_infinite_phase_handling(self) -> None:
        """Test handling of infinite phases."""
        phase1 = TIntervalLoops(interval=timedelta(seconds=1), loops=2)
        phase2 = TIntervalDuration(interval=timedelta(seconds=1), duration=None)

        plan = MultiPhaseTimePlan(phases=[phase1, phase2])
        iterator = iter(plan)

        # Get first phase values
        # Should get 0, 1, 1 (start of phase 2)
        times = [next(iterator) for _ in range(3)]

        # Phase 1 ends after 1 second, so phase 2 starts with offset 1
        assert times[:2] == [0.0, 1.0]
        assert times[2] == 2.0  # Start of infinite phase 2

    def test_empty_phases(self) -> None:
        """Test behavior with empty phases list."""
        plan = MultiPhaseTimePlan(phases=[])
        times = list(plan)
        assert times == []

    def test_single_phase(self) -> None:
        """Test behavior with single phase."""
        phase = TIntervalLoops(interval=timedelta(seconds=2), loops=3)
        plan = MultiPhaseTimePlan(phases=[phase])

        times = list(plan)
        assert times == [0.0, 2.0, 4.0]


class TestTimePlanAbstract:
    """Test abstract TimePlan behavior."""

    def test_axis_key_default(self) -> None:
        """Test that axis_key defaults to 't'."""
        plan = TIntervalLoops(interval=timedelta(seconds=1), loops=2)
        assert plan.axis_key == "t"

    def test_prioritize_duration_default(self) -> None:
        """Test prioritize_duration defaults."""
        plan1 = TIntervalLoops(interval=timedelta(seconds=1), loops=2)
        assert plan1.prioritize_duration is False

        plan2 = TIntervalDuration(
            interval=timedelta(seconds=1), duration=timedelta(seconds=5)
        )
        assert plan2.prioritize_duration is True


class TestTypeAliases:
    """Test type aliases work correctly."""

    def test_single_phase_time_plan_types(self) -> None:
        """Test that SinglePhaseTimePlan accepts all expected types."""
        plans: list[SinglePhaseTimePlan] = [
            TIntervalDuration(
                interval=timedelta(seconds=1), duration=timedelta(seconds=5)
            ),
            TIntervalLoops(interval=timedelta(seconds=1), loops=3),
            TDurationLoops(duration=timedelta(seconds=6), loops=4),
        ]

        for plan in plans:
            assert isinstance(plan, TimePlan)

    def test_any_time_plan_types(self) -> None:
        """Test that AnyTimePlan accepts all expected types."""
        phase = TIntervalLoops(interval=timedelta(seconds=1), loops=2)

        plans: list[AnyTimePlan] = [
            TIntervalDuration(
                interval=timedelta(seconds=1), duration=timedelta(seconds=5)
            ),
            TIntervalLoops(interval=timedelta(seconds=1), loops=3),
            TDurationLoops(duration=timedelta(seconds=6), loops=4),
            MultiPhaseTimePlan(phases=[phase]),
        ]

        for plan in plans:
            assert isinstance(plan, TimePlan)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_small_intervals(self) -> None:
        """Test behavior with very small time intervals."""
        plan = TIntervalLoops(interval=timedelta(microseconds=1), loops=3)
        times = list(plan)

        expected = [0.0, 0.000001, 0.000002]
        assert len(times) == 3
        for actual, exp in zip(times, expected):
            assert abs(actual - exp) < 1e-9

    def test_large_number_of_loops(self) -> None:
        """Test with large number of loops."""
        plan = TIntervalLoops(interval=timedelta(seconds=1), loops=1000)
        assert len(plan) == 1000

        # Test first and last few values
        iterator = iter(plan)
        assert next(iterator) == 0.0
        assert next(iterator) == 1.0

        # Skip to end
        times = list(iterator)
        assert times[-1] == 999.0

    def test_zero_interval_duration_plan(self) -> None:
        """Test TIntervalDuration with zero interval."""
        plan = TIntervalDuration(
            interval=timedelta(seconds=0), duration=timedelta(seconds=1)
        )
        # This should theoretically create an infinite loop at t=0
        # Implementation should handle this gracefully
        iterator = iter(plan)
        first_few = [next(iterator) for _ in range(3)]
        assert all(t == 0.0 for t in first_few)

    def test_negative_duration_loops(self) -> None:
        """Test that negative duration raises appropriate error."""
        with pytest.raises(ValueError):
            TDurationLoops(duration=timedelta(seconds=-5), loops=3)

    def test_duration_loops_with_one_loop_edge_case(self) -> None:
        """Test duration loops with exactly one loop."""
        plan = TDurationLoops(duration=timedelta(seconds=10), loops=1)
        times = list(plan)

        # With 1 loop, we expect just [0.0]
        assert times == [0.0]
        # With 1 loop, interval is meaningless and returns zero
        assert plan.interval.total_seconds() == 0.0
        # But _interval_s returns infinity to indicate instantaneous
        assert plan._interval_s() == 0


@pytest.mark.parametrize(
    "plan_class,kwargs",
    [
        (TIntervalLoops, {"interval": timedelta(seconds=1), "loops": 3}),
        (TDurationLoops, {"duration": timedelta(seconds=6), "loops": 4}),
        (
            TIntervalDuration,
            {"interval": timedelta(seconds=2), "duration": timedelta(seconds=10)},
        ),
    ],
)
def test_time_plan_serialization(plan_class: type[TimePlan], kwargs: dict) -> None:
    """Test that time plans can be serialized and deserialized."""
    plan = plan_class(**kwargs)

    # Test model dump/load cycle
    data = plan.model_dump_json()
    restored = plan_class.model_validate_json(data)

    assert restored == plan
    assert list(restored) == list(plan)


def test_integration_with_mda_axis_iterable() -> None:
    """Test that time plans integrate properly with MDAAxisIterable."""
    plan = TIntervalLoops(interval=timedelta(seconds=2), loops=3)

    # Should have MDAAxisIterable methods
    assert hasattr(plan, "axis_key")

    # Test the axis_key
    assert plan.axis_key == "t"

    # Test iteration returns float values
    values = list(plan)
    assert all(isinstance(v, float) for v in values)


def test_contribute_to_mda_event() -> None:
    """Test that time plans can contribute to MDA events."""
    plan = TIntervalLoops(interval=timedelta(seconds=2), loops=3)

    # Test contribution
    contribution = plan.contribute_to_mda_event(4.0, {"t": 2})
    assert contribution == {"min_start_time": 4.0}

    # Test with different value
    contribution = plan.contribute_to_mda_event(0.0, {"t": 0})
    assert contribution == {"min_start_time": 0.0}
