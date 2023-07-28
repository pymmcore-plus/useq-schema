from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Iterator, Mapping, Tuple, TypeVar, Union

from pydantic import validator

if TYPE_CHECKING:
    from typing import Final

KT = TypeVar("KT")
VT = TypeVar("VT")


# could be an enum, but this more easily allows Axis.Z to be a string
class Axis:
    """Recognized axis names."""

    TIME: Final[str] = "t"
    POSITION: Final[str] = "p"
    GRID: Final[str] = "g"
    CHANNEL: Final[str] = "c"
    Z: Final[str] = "z"


# note: order affects the default axis_order in MDASequence
AXES: Final[tuple[str, ...]] = (
    Axis.TIME,
    Axis.POSITION,
    Axis.GRID,
    Axis.CHANNEL,
    Axis.Z,
)


class ReadOnlyDict(Mapping[KT, VT]):
    def __init__(
        self, data: Union[Mapping[KT, VT], Iterable[Tuple[KT, VT]]] = ()
    ) -> None:
        self._data = dict(data)

    def __getitem__(self, key: KT) -> VT:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[KT]:
        return iter(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


def list_cast(field: str) -> classmethod:
    v = validator(field, pre=True, allow_reuse=True, check_fields=False)
    return v(list)
