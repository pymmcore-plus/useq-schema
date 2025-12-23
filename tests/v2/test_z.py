"""Tests for v2 Z plans module."""

from __future__ import annotations

import pytest

from useq._enums import Axis
from useq.v2 import (
    MDAEvent,
    Position,
    ZAboveBelow,
    ZAbsolutePositions,
    ZPlan,
    ZRangeAround,
    ZRelativePositions,
    ZTopBottom,
)


class TestZTopBottom:
    """Test ZTopBottom plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and attributes."""
        plan = ZTopBottom(top=10.0, bottom=0.0, step=2.0)
        assert plan.top == 10.0
        assert plan.bottom == 0.0
        assert plan.step == 2.0
        assert plan.go_up is True
        assert plan.axis_key == Axis.Z

    def test_positions_go_up(self) -> None:
        """Test positions when go_up is True."""
        plan = ZTopBottom(top=4.0, bottom=0.0, step=1.0, go_up=True)
        positions = [p.z for p in plan]
        expected = [0.0, 1.0, 2.0, 3.0, 4.0]
        assert positions == expected

    def test_positions_go_down(self) -> None:
        """Test positions when go_up is False."""
        plan = ZTopBottom(top=4.0, bottom=0.0, step=1.0, go_up=False)
        positions = [p.z for p in plan]
        expected = [4.0, 3.0, 2.0, 1.0, 0.0]
        assert positions == expected

    def test_is_relative(self) -> None:
        """Test is_relative property."""
        plan = ZTopBottom(top=4.0, bottom=0.0, step=1.0)
        assert plan.is_relative is False

    def test_num_positions(self) -> None:
        """Test num_positions method."""
        plan = ZTopBottom(top=4.0, bottom=0.0, step=1.0)
        assert len(plan) == 5

    def test_start_stop_step(self) -> None:
        """Test _start_stop_step method."""
        plan = ZTopBottom(top=10.0, bottom=2.0, step=1.5)
        start, stop, step = plan._start_stop_step()
        assert start == 2.0
        assert stop == 10.0
        assert step == 1.5

    def test_contribute_to_mda_event(self) -> None:
        """Test contribute_to_mda_event method."""
        plan = ZTopBottom(top=10.0, bottom=0.0, step=2.0)
        contribution = plan.contribute_to_mda_event(Position(z=5.0), {"z": 2})
        assert contribution == {"z_pos": 5.0, "is_relative": False}


class TestZRangeAround:
    """Test ZRangeAround plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and attributes."""
        plan = ZRangeAround(range=4.0, step=1.0)
        assert plan.range == 4.0
        assert plan.step == 1.0
        assert plan.go_up is True
        assert plan.axis_key == Axis.Z

    def test_positions_symmetric(self) -> None:
        """Test symmetric positions around center."""
        plan = ZRangeAround(range=4.0, step=1.0, go_up=True)
        positions = [p.z for p in plan]
        expected = [-2.0, -1.0, 0.0, 1.0, 2.0]
        assert positions == expected

    def test_start_stop_step(self) -> None:
        """Test _start_stop_step method."""
        plan = ZRangeAround(range=6.0, step=1.5)
        start, stop, step = plan._start_stop_step()
        assert start == -3.0
        assert stop == 3.0
        assert step == 1.5

    def test_is_relative(self) -> None:
        """Test is_relative property."""
        plan = ZRangeAround(range=4.0, step=1.0)
        assert plan.is_relative is True


class TestZAboveBelow:
    """Test ZAboveBelow plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and attributes."""
        plan = ZAboveBelow(above=3.0, below=2.0, step=1.0)
        assert plan.above == 3.0
        assert plan.below == 2.0
        assert plan.step == 1.0
        assert plan.axis_key == Axis.Z

    def test_positions_asymmetric(self) -> None:
        """Test asymmetric positions."""
        plan = ZAboveBelow(above=3.0, below=2.0, step=1.0, go_up=True)
        positions = [p.z for p in plan]
        expected = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
        assert positions == expected

    def test_start_stop_step(self) -> None:
        """Test _start_stop_step method."""
        plan = ZAboveBelow(above=4.0, below=3.0, step=0.5)
        start, stop, step = plan._start_stop_step()
        assert start == -3.0
        assert stop == 4.0
        assert step == 0.5

    def test_negative_values(self) -> None:
        """Test with negative input values (should be made absolute)."""
        plan = ZAboveBelow(above=-2.0, below=-3.0, step=1.0)
        start, stop, step = plan._start_stop_step()
        assert start == -3.0  # abs(-3.0) = 3.0, then -3.0
        assert stop == 2.0  # abs(-2.0) = 2.0, then +2.0
        assert step == 1.0


class TestZRelativePositions:
    """Test ZRelativePositions plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and attributes."""
        plan = ZRelativePositions(relative=[1.0, 2.0, 3.0])
        assert plan.relative == [1.0, 2.0, 3.0]
        assert plan.axis_key == Axis.Z
        assert len(plan) == 3
        assert plan.is_relative is True

    def test_list_cast_validator(self) -> None:
        """Test that input is cast to list."""
        plan = ZRelativePositions(relative=(1.0, 2.0, 3.0))  # tuple input
        assert plan.relative == [1.0, 2.0, 3.0]  # should be cast to list


class TestZAbsolutePositions:
    """Test ZAbsolutePositions plan."""

    def test_basic_creation(self) -> None:
        """Test basic creation and attributes."""
        plan = ZAbsolutePositions(absolute=[10.0, 20.0, 30.0])
        assert plan.absolute == [10.0, 20.0, 30.0]
        assert plan.axis_key == Axis.Z
        assert len(plan) == 3
        assert plan.is_relative is False

    def test_list_cast_validator(self) -> None:
        """Test that input is cast to list."""
        plan = ZAbsolutePositions(absolute=(10.0, 20.0, 30.0))  # tuple input
        assert plan.absolute == [10.0, 20.0, 30.0]  # should be cast to list


class TestZPlanBase:
    """Test ZPlan base class functionality."""

    def test_axis_key_default(self) -> None:
        """Test that axis_key defaults to 'z'."""
        plan = ZRelativePositions(relative=[1.0, 2.0])
        assert plan.axis_key == "z"

    def test_mda_axis_iterable_interface(self) -> None:
        """Test that Z plans implement MDAAxisIterable interface."""
        plan = ZTopBottom(top=2.0, bottom=0.0, step=1.0)

        # Should have MDAAxisIterable methods
        assert hasattr(plan, "axis_key")
        assert hasattr(plan, "contribute_to_mda_event")

        # Test iteration returns float values
        values = [p.z for p in plan]
        assert all(isinstance(v, float) for v in values)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_step_single_position(self) -> None:
        """Test behavior with zero step size."""
        plan = ZTopBottom(top=5.0, bottom=5.0, step=0.0)
        positions = [p.z for p in plan]
        assert positions == [5.0]
        assert len(plan) == 1

    def test_very_small_steps(self) -> None:
        """Test with very small step sizes."""
        plan = ZTopBottom(top=1.0, bottom=0.0, step=0.1)
        positions = [p.z for p in plan]
        assert len(positions) == 11
        assert positions[0] == pytest.approx(0.0)
        assert positions[-1] == pytest.approx(1.0)

    def test_empty_position_lists(self) -> None:
        """Test with empty position lists."""
        plan = ZRelativePositions(relative=[])
        positions = [p.z for p in plan]
        assert positions == []
        assert len(plan) == 0

    def test_single_position_lists(self) -> None:
        """Test with single position in lists."""
        plan = ZAbsolutePositions(absolute=[42.0])
        positions = [p.z for p in plan]
        assert positions == [42.0]
        assert len(plan) == 1

    def test_large_ranges(self) -> None:
        """Test with large Z ranges."""
        plan = ZTopBottom(top=1000.0, bottom=0.0, step=100.0)
        positions = [p.z for p in plan]
        assert len(positions) == 11
        assert positions[0] == 0.0
        assert positions[-1] == 1000.0


class TestSerialization:
    """Test serialization and deserialization."""

    @pytest.mark.parametrize(
        "plan_class,kwargs",
        [
            (ZTopBottom, {"top": 10.0, "bottom": 0.0, "step": 2.0}),
            (ZRangeAround, {"range": 4.0, "step": 1.0}),
            (ZAboveBelow, {"above": 3.0, "below": 2.0, "step": 1.0}),
            (ZRelativePositions, {"relative": [1.0, 2.0, 3.0]}),
            (ZAbsolutePositions, {"absolute": [10.0, 20.0, 30.0]}),
        ],
    )
    def test_z_plan_serialization(self, plan_class: type[ZPlan], kwargs: dict) -> None:
        """Test that Z plans can be serialized and deserialized."""
        original_plan = plan_class(**kwargs)

        # Test JSON serialization round-trip
        json_data = original_plan.model_dump_json()
        restored_plan = plan_class.model_validate_json(json_data)

        # Should be equivalent
        assert list(original_plan) == list(restored_plan)
        assert original_plan.axis_key == restored_plan.axis_key
        if hasattr(original_plan, "go_up"):
            # Check go_up attribute if it exists
            assert original_plan.go_up == restored_plan.go_up  # type: ignore


class TestTypeAliases:
    """Test type aliases and union types."""

    def test_any_z_plan_types(self) -> None:
        """Test that AnyZPlan includes all Z plan types."""
        plans = [
            ZTopBottom(top=10.0, bottom=0.0, step=2.0),
            ZRangeAround(range=4.0, step=1.0),
            ZAboveBelow(above=3.0, below=2.0, step=1.0),
            ZRelativePositions(relative=[1.0, 2.0, 3.0]),
            ZAbsolutePositions(absolute=[10.0, 20.0, 30.0]),
        ]

        for plan in plans:
            # Should be valid instances of AnyZPlan
            assert isinstance(plan, ZPlan)


def test_contribute_to_mda_event_integration() -> None:
    """Test integration with MDAEvent.Kwargs."""
    plan = ZTopBottom(top=10.0, bottom=0.0, step=5.0)

    # Test contribution
    contribution = plan.contribute_to_mda_event(Position(z=7.5), {"z": 1})
    assert contribution == {"z_pos": 7.5, "is_relative": False}

    # Test that the contribution can be used to create an MDAEvent
    event_data = {"index": {"z": 1}, **contribution}
    event = MDAEvent(**event_data)
    assert event.z_pos == 7.5


def test_integration_with_mda_axis_iterable() -> None:
    """Test that Z plans integrate properly with MDAAxisIterable."""
    plan = ZTopBottom(top=4.0, bottom=0.0, step=2.0)

    # Should have MDAAxisIterable methods
    assert hasattr(plan, "axis_key")

    # Test the axis_key
    assert plan.axis_key == Axis.Z

    # Test iteration returns float values
    values = [p.z for p in plan]
    assert all(isinstance(v, float) for v in values)
    assert values == [0.0, 2.0, 4.0]
