from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    NamedTuple,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
)

from pydantic import Field, validator
from pydantic.types import PositiveFloat

from ._base_model import UseqModel
from ._utils import ReadOnlyDict

if TYPE_CHECKING:
    from ._mda_sequence import MDASequence

    ReprArgs = Sequence[Tuple[Optional[str], Any]]


class Channel(UseqModel):
    config: str
    group: str = "Channel"


class PropertyTuple(NamedTuple):
    device_name: str
    property_name: str
    property_value: Any


def _readonly(self: object, *_: Any, **__: Any) -> NoReturn:
    raise RuntimeError(f"Cannot modify {type(self).__name__}")


class MDAEvent(UseqModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    index: ReadOnlyDict[str, int] = Field(default_factory=ReadOnlyDict)
    channel: Optional[Channel] = None
    exposure: Optional[PositiveFloat] = None
    min_start_time: Optional[float] = None  # time in sec
    pos_name: Optional[str] = None
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None
    z_pos: Optional[float] = None
    properties: Optional[Sequence[PropertyTuple]] = None
    sequence: Optional[MDASequence] = Field(default=None, repr=False)
    global_index: int = Field(default=0, repr=False)

    # action
    # keep shutter open between channels/steps

    @validator("index", pre=True)
    def validate_index(cls, v: dict) -> ReadOnlyDict[str, int]:
        return ReadOnlyDict(v)

    def __repr_args__(self) -> ReprArgs:
        d = self.__dict__.copy()
        d.pop("sequence")
        return list(d.items())

    def to_pycromanager(self) -> dict:
        d: Dict[str, Any] = {
            "exposure": self.exposure,
            "axes": {},
            "z": self.z_pos,
            "x": self.x_pos,
            "y": self.y_pos,
            "min_start_time": self.min_start_time,
            "channel": self.channel and self.channel.dict(),
        }
        if "p" in self.index:
            d["axes"]["position"] = self.index["p"]
        if "t" in self.index:
            d["axes"]["time"] = self.index["t"]
        if "z" in self.index:
            d["axes"]["z"] = self.index["z"]
        if self.properties:
            d["properties"] = [list(p) for p in self.properties]

        for key, value in list(d.items()):
            if value is None:
                d.pop(key)
        return d
