from __future__ import annotations

from typing import TYPE_CHECKING

from useq._mda_event import MDAEvent

# transformers.py
from useq._utils import Axis
from useq.v2._axes_iterator import EventTransform  # helper you already have

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from useq._hardware_autofocus import AxesBasedAF


# Global state to share reset_event_timer state across all sequences (like v1)
_global_last_t_idx: int = -1


def reset_global_timer_state() -> None:
    """Reset the global timer state. Should be called at the start of each sequence."""
    global _global_last_t_idx
    _global_last_t_idx = -1


class KeepShutterOpenTransform(EventTransform[MDAEvent]):
    """Replicates the v1 `keep_shutter_open_across` behaviour.

    Parameters
    ----------
    axes
        Tuple of axis names (`"p"`, `"t"`, `"c"`, `"z"`, …) on which the shutter
        may stay open when only **they** change between consecutive events.
    """

    def __init__(self, axes: tuple[str, ...]):
        self.axes = axes

    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        if (nxt := make_next_event()) is None:  # last event → nothing to tweak
            return [event]

        # keep shutter open iff every axis that *changes* is in `self.axes`
        if all(
            ax in self.axes
            for ax, idx in event.index.items()
            if idx != nxt.index.get(ax)
        ):
            event = event.model_copy(update={"keep_shutter_open": True})

        return [event]


class ResetEventTimerTransform(EventTransform[MDAEvent]):
    """Marks the first frame of each timepoint with ``reset_event_timer=True``."""

    def __init__(self) -> None:
        # Use global state to match v1 behavior where _last_t_idx is shared
        # across all nested sequences
        pass

    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        global _global_last_t_idx

        # No time axis → nothing to do
        if Axis.TIME not in event.index:
            return [event]

        # Reset timer when t=0 and the last t_idx wasn't 0 (matching v1 behavior)
        current_t_idx = event.index.get(Axis.TIME, 0)
        if current_t_idx == 0 and _global_last_t_idx != 0:
            event = event.model_copy(update={"reset_event_timer": True})

        # Update the global last t index for next time
        _global_last_t_idx = current_t_idx
        return [event]


class AutoFocusTransform(EventTransform[MDAEvent]):
    """Insert hardware-autofocus events created by an ``AutoFocusPlan``.

    Parameters
    ----------
    plan_getter :
        Function that returns the *active* autofocus plan for the
        current event.  By default we use ``event.sequence.autofocus_plan``,
        but you can plug in something smarter if you support
        per-position overrides.
    """

    priority = -1

    def __init__(self, af_plan: AxesBasedAF) -> None:
        self._af_plan = af_plan

    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],  # unused, but required
    ) -> Iterable[MDAEvent]:
        # Skip autofocus when no axes specified
        af_axes = self._af_plan.axes
        if not af_axes:
            return [event]

        # Determine if any specified axis has changed (or first event)
        trigger = False
        if prev_event is None:
            trigger = True
        else:
            for axis in af_axes:
                if prev_event.index.get(axis) != event.index.get(axis):
                    trigger = True
                    break

        if trigger:
            updates: dict[str, object] = {"action": self._af_plan.as_action()}
            if event.z_pos is not None and event.sequence is not None:
                zplan = event.sequence.z_plan
                if zplan and zplan.is_relative and "z" in event.index:
                    try:
                        positions = list(zplan)
                        val = positions[event.index["z"]]
                        offset = val.z if hasattr(val, "z") else val
                        updates["z_pos"] = event.z_pos - offset
                    except (IndexError, AttributeError):
                        pass  # fallback to default

            af_event = event.model_copy(update=updates)
            return [af_event, event]

        return [event]
