from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    runtime_checkable,
)

from pydantic import PrivateAttr

from useq._actions import HardwareAutofocus
from useq._base_model import FrozenModel

if TYPE_CHECKING:
    from useq import MDAEvent


@runtime_checkable
class EventModifierProtocol(Protocol):
    """Callable object that can modify the yielding of events in a sequence.

    During iteration of an MDASequence, this object will be called with the event
    about to be yielded (`event`), and the upcoming event in the sequence
    (`next_event`), which may be `None` if this is the last event in the sequence.
    It should return:

        1. `MDAEvent`: A possibly-modified event to *replace* this event. The input
            event may be returned unmodified to keep the event unchanged.
        1. `Sequence[MDAEvent]`: event(s) to be inserted before `event`. (The events
            will *NOT* be passed to other event modifiers in the chain).
        1. `None`: to skip this event altogether (i.e. "block" the event.)
    """

    def __call__(
        self, event: MDAEvent, next_event: MDAEvent | None
    ) -> MDAEvent | Sequence[MDAEvent] | None:
        ...

    @classmethod
    def __get_validators__(cls) -> Generator[Callable, None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> EventModifierProtocol:
        breakpoint()


class AxesBasedAF(FrozenModel):
    """Base class for hardware autofocus plans.

    Attributes
    ----------
    autofocus_device_name : str
        Name of the hardware autofocus z device.
    axes : Tuple[str, ...]
        Tuple of axis label to use for hardware autofocus.  At every event in which
        *any* axis in this tuple is change, autofocus will be performed.  For example,
        if `axes` is `('p',)` then autofocus will be performed every time the `p` axis
        is change, (in other words: every time the position is changed.).
    autofocus_motor_offset : float | None
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    """

    autofocus_device_name: str
    axes: Tuple[str, ...]
    autofocus_motor_offset: Optional[float] = None
    type: Literal["hardware_autofocus"] = "hardware_autofocus"

    _previous_indices: dict[str, int] = PrivateAttr(default_factory=dict)

    def __call__(
        self, event: MDAEvent, next_event: MDAEvent | None
    ) -> MDAEvent | Sequence[MDAEvent]:
        """Return an autofocus [`useq.MDAEvent`][] if autofocus should be performed.

        The z position of the new [`useq.MDAEvent`][] is also updated if a relative
        zplan is provided since autofocus shuld be performed on the home z stack
        position.
        """
        if not self._should_autofocus(event):
            return event

        updates: dict[str, Any] = {"action": self._as_action()}
        if event.z_pos is not None and event.sequence is not None:
            zplan = event.sequence.z_plan
            if zplan and zplan.is_relative and "z" in event.index:
                updates["z_pos"] = event.z_pos - list(zplan)[event.index["z"]]

        # insert the autofocus event before the current event
        return (event.copy(update=updates),)

    def _should_autofocus(self, event: MDAEvent) -> bool:
        """Return `True` if autofocus should be performed at this event.

        Will return `True` if any of the axes specified in `axes` have changed from the
        previous event.
        """
        self._previous_indices, previous = dict(event.index), self._previous_indices
        return any(
            axis in self.axes and previous.get(axis) != index
            for axis, index in event.index.items()
        )

    def _as_action(self) -> HardwareAutofocus:
        """Return a [`useq.HardwareAutofocus`][] for this autofocus plan."""
        return HardwareAutofocus(
            autofocus_device_name=self.autofocus_device_name,
            autofocus_motor_offset=self.autofocus_motor_offset,
        )


class KeepShutterOpen(FrozenModel):
    """Base class for hardware autofocus plans.

    Attributes
    ----------
    axes : Tuple[str, ...]
        A tuple of axes `str` across which the illumination shutter should be kept open.
        Resulting events will have `keep_shutter_open` set to `True` if and only if
        ALL axes whose indices are changing are in this tuple. For example, if
        `keep_shutter_open_across=('z',)`, then the shutter would be kept open between
        events axes {'t': 0, 'z: 0} and {'t': 0, 'z': 1}, but not between
        {'t': 0, 'z': 0} and {'t': 1, 'z': 0}.
    """

    axes: Tuple[str, ...]
    type: Literal["keep_shutter_open"] = "keep_shutter_open"

    def __call__(self, event: MDAEvent, next_event: MDAEvent | None) -> MDAEvent:
        """Add `keep_shutter_open` to the event if the appropriate.

        `keep_shutter_open` should be set to `True` if and only if ALL axes whose
        indices are changing are in the KeepShutterOpen.axes tuple.
        """
        if next_event and all(
            axis in self.axes
            for axis, idx in event.index.items()
            if idx != next_event.index.get(axis)
        ):
            event = event.copy(update={"keep_shutter_open": True})
        return event


EventModifier = Union[AxesBasedAF, KeepShutterOpen, EventModifierProtocol]
