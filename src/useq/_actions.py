from typing_extensions import Literal

from ._base_model import FrozenModel


class Action(FrozenModel):
    """Base class for a [`MDAEvent`][useq.MDAEvent] `action`.

    An `Action` specifies what task should be performed during a
    [`MDAEvent`][useq.MDAEvent]. An `Action` can be for example used to acquire an
    image ([`AcquireImage`][useq.AcquireImage]) or to perform a hardware autofocus
    ([`HardwareAutofocus`][useq.HardwareAutofocus]).

    Parameters
    ----------
    type : str
        Type of the action that should be performed at the [`useq.MDAEvent`][].
    """

    type: str


class AcquireImage(Action):
    """[`Action`][useq.Action] to acquire an image.

    Attributes
    ----------
    type : Literal["acquire_image"]
        This action can be used to acquire an image.
    """

    type: Literal["acquire_image"] = "acquire_image"


class HardwareAutofocus(Action):
    """[`Action`][useq.Action] to perform a hardware autofocus.

    See also [`AutoFocusPlan`][useq.AutoFocusPlan].

    Attributes
    ----------
    type : Literal["hardware_autofocus"]
        This action can be used to trigger hardware autofocus.
    autofocus_device_name : str
        The name of the hardware autofocus device.
    autofocus_motor_offset: float
        Before autofocus is performed, the autofocus motor should be moved to this
        offset.
    max_retries : int
        The number of retries if autofocus fails. By default, 3.
    """

    type: Literal["hardware_autofocus"] = "hardware_autofocus"
    autofocus_device_name: str
    autofocus_motor_offset: float
    max_retries: int = 3
