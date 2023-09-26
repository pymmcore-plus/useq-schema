from typing import Optional, Union

from typing_extensions import Literal

from useq._base_model import FrozenModel


class Action(FrozenModel):
    """Base class for a [`useq.MDAEvent`][] action.

    An `Action` specifies what task should be performed during a
    [`useq.MDAEvent`][]. An `Action` can be for example used to acquire an
    image ([`useq.AcquireImage`][]) or to perform a hardware autofocus
    ([`useq.HardwareAutofocus`][]).

    Attributes
    ----------
    type : str
        Type of the action that should be performed at the [`useq.MDAEvent`][].
    """

    type: str


class AcquireImage(Action):
    """[`useq.Action`][] to acquire an image.

    Attributes
    ----------
    type : Literal["acquire_image"]
        This action can be used to acquire an image.
    """

    type: Literal["acquire_image"] = "acquire_image"


class HardwareAutofocus(Action):
    """[`useq.Action`][] to perform a hardware autofocus.

    See also [`useq.AutoFocusPlan`][].

    Attributes
    ----------
    type : Literal["hardware_autofocus"]
        This action can be used to trigger hardware autofocus.
    autofocus_device_name : str, optional
        The name of the autofocus offset motor device (if applicable).  If `None`,
        acquisition engines may attempt to set the offset however they see fit (such as
        using a current or default autofocus device.)
    autofocus_motor_offset: float, optional
        Before autofocus is performed, the autofocus motor should be moved to this
        offset, if applicable. (Not all autofocus devices have an offset motor.)
        If None, the autofocus motor should not be moved.
    max_retries : int
        The number of retries if autofocus fails. By default, 3.
    """

    type: Literal["hardware_autofocus"] = "hardware_autofocus"
    autofocus_device_name: Optional[str] = None
    autofocus_motor_offset: Optional[float] = None
    max_retries: int = 3


AnyAction = Union[HardwareAutofocus, AcquireImage]
