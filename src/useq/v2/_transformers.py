from collections.abc import Callable, Iterable

# transformers.py
from useq._enums import Axis
from useq._hardware_autofocus import AxesBasedAF
from useq._mda_event import MDAEvent
from useq.v2._axes_iterator import EventTransform  # helper you already have


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

    # ---- EventTransform API -------------------------------------------------
    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        nxt = make_next_event()  # cached, so cheap even if many transformers call
        if nxt is None:  # last event → nothing to tweak
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

    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        cur_t = event.index.get(Axis.TIME)
        if cur_t is None:  # no time axis → nothing to do
            return [event]

        prev_t = prev_event.index.get(Axis.TIME) if prev_event else None
        if cur_t == 0 and prev_t != 0:
            event = event.model_copy(update={"reset_event_timer": True})
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

    def __init__(self, af_plan: AxesBasedAF) -> None:
        self._af_plan = af_plan

    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],  # unused, but required
    ) -> Iterable[MDAEvent]:
        # should autofocus if any of the axes in the autofocus plan
        # changed from the previous event, or if this is the first event
        if prev_event is None or any(
            axis in self._af_plan.axes and prev_event.index.get(axis) != index
            for axis, index in event.index.items()
        ):
            updates = {"action": self._af_plan.as_action()}
            # if event.z_pos is not None and event.sequence is not None:
            #     zplan = event.sequence.z_plan
            #     if zplan and zplan.is_relative and "z" in event.index:
            #         updates["z_pos"] = event.z_pos - list(zplan)[event.index["z"]]
            af_event = event.model_copy(update=updates)
            return [af_event, event]

        return [event]
