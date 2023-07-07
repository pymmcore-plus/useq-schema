from typing import Callable, Optional, Tuple, Union

from ._base_model import FrozenModel


class AutoFocusPlan(FrozenModel):
    """Base class for hardware autofocus plans.

    Attributes
    ----------
    autofocus_z_device_name : str
        Name of the hardware autofocus z device.
    af_motor_offset : float | None
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    z_stage_position : float | None
        Before autofocus is performed, the z stage should be moved to this position.
        (Note: the Z-stage is the "main" z-axis, and is not the same as the autofocus
        device.)
    """

    autofocus_z_device_name: str
    af_motor_offset: Optional[float] = None
    z_stage_position: Optional[float] = None


class AxesBasedAF(AutoFocusPlan):
    """Autofocus plan that performs autofocus when any of the specified axes change.

    Attributes
    ----------
    axes : Tuple[str, ...]
        Tuple of axis label to use for hardware autofocus.  At every event in which
        *any* axis in this tuple is change, autofocus will be performed.  For example,
        if `axes` is `('p',)` then autofocus will be performed every time the `p` axis
        is change, (in other words: every time the position is changed.)
    """

    axes: Tuple[str, ...]


class PredicateAF(AutoFocusPlan):
    """An autofocus plan that performs autofocus when a callable evaluates to `True`.

    The callable should accept ...

    Parameters
    ----------
    AutoFocusPlan : _type_
        _description_
    """

    predicate: Callable[..., bool]


class NoAF(AutoFocusPlan):
    """No hardware autofocus plan."""

    autofocus_z_device_name: str = "__no_autofocus__"
    # axes: Optional[Tuple[str, ...]] = None

    def __bool__(self) -> bool:
        return False


AnyAF = Union[AxesBasedAF, NoAF]
