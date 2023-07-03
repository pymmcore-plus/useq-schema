from typing import Optional, Tuple, Union

from ._base_model import FrozenModel


class AutoFocusPlan(FrozenModel):
    """Base class for hardware autofocus plans."""

    autofocus_z_device_name: Optional[str]
    z_autofocus_position: Optional[float]
    z_focus_position: Optional[float]
    axes: Optional[Tuple[str, ...]]


class PerformAF(AutoFocusPlan):
    """Perform hardware autofocus plan.

    Attributes
    ----------
    autofocus_z_device_name : str
        Name of the autofocus z device.
    z_autofocus_position : float | None
        Optional autofocus z motor position.
    z_focus_position : float | None
        Optional focus z motor position.
    axes : Tuple[str, ...] | None
        Tuple of axis to use for hardware autofocus.
    """

    autofocus_z_device_name: str
    z_autofocus_position: Optional[float]
    z_focus_position: Optional[float]
    axes: Tuple[str, ...]


class NoAF(AutoFocusPlan):
    """No hardware autofocus plan."""

    autofocus_z_device_name: Optional[str] = None
    z_autofocus_position: Optional[float] = None
    z_focus_position: Optional[float] = None
    axes: Optional[Tuple[str, ...]] = None


AnyAF = Union[PerformAF, NoAF]
