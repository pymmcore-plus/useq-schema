from typing import Optional, Union

from pydantic import ConfigDict, Field, TypeAdapter, field_validator
from pydantic_core import PydanticSerializationError
from typing_extensions import Literal

from useq._base_model import FrozenModel

_dict_adapter = TypeAdapter(dict, config=ConfigDict(defer_build=True))


class Action(FrozenModel):
    """Base class for a [`useq.MDAEvent`][] action.

    An `Action` specifies what task should be performed during a
    [`useq.MDAEvent`][]. An `Action` can be for example used to acquire an
    image ([`useq.AcquireImage`][]) or to perform a hardware autofocus
    ([`useq.HardwareAutofocus`][]).  An action of `None` implies `AcquireImage`.

    You may use `CustomAction` to indicate any custom action, with the `data` attribute
    containing any data required to perform the custom action.

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

    type: Literal["acquire_image"] = "acquire_image"  # pyright: ignore[reportIncompatibleVariableOverride]


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

    type: Literal["hardware_autofocus"] = "hardware_autofocus"  # pyright: ignore[reportIncompatibleVariableOverride]
    autofocus_device_name: Optional[str] = None
    autofocus_motor_offset: Optional[float] = None
    max_retries: int = 3


class CustomAction(Action):
    """[`useq.Action`][] to perform a custom action.

    This is a generic user action that can be used to represent anything that is not
    covered by the other action types, such as a microfluidic event, or a
    photostimulation, etc...

    The `data` attribute is a dictionary that can contain any data that is needed to
    perform the custom action.  It *must* be serializable to JSON by `pydantic`.

    Attributes
    ----------
    type : Literal["custom"]
        This action can be used to perform a custom action.
    name : str, optional
        A name for the custom action (not to be confused with the `type` attribute,
        which must always be `"custom"`).
    data : dict, optional
        Custom data associated with the action.
    """

    type: Literal["custom"] = "custom"  # pyright: ignore[reportIncompatibleVariableOverride]
    name: str = ""
    data: dict = Field(default_factory=dict)

    @field_validator("data", mode="after")
    @classmethod
    def _ensure_serializable(cls, data: dict) -> dict:
        try:
            _dict_adapter.serializer.to_json(data)
        except PydanticSerializationError as e:
            raise ValueError(
                f"`CustomAction.data` must be JSON serializable, but is not:\n  {e}.\n"
                "  (You may use a pydantic object for custom serialization).\n   "
            ) from e
        return data


AnyAction = Union[HardwareAutofocus, AcquireImage, CustomAction]
