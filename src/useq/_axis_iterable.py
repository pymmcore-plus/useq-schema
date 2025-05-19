from __future__ import annotations

from collections.abc import Iterator, Sized
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NamedTuple,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel

if TYPE_CHECKING:
    from useq._iter_sequence import MDAEventDict


# ------ Protocol that can be used as a field annotation in a Pydantic model ------

T = TypeVar("T")


class IterItem(NamedTuple):
    """An item in an iteration sequence."""

    axis_key: str
    axis_index: int
    value: Any
    axis_iterable: AxisIterable


@runtime_checkable
class AxisIterable(Protocol[T]):
    @property
    def axis_key(self) -> str:
        """A string id representing the axis. Prefer lowercase."""

    def __iter__(self) -> Iterator[T]:
        """Iterate over the axis."""

    def create_event_kwargs(self, val: T) -> MDAEventDict:
        """Convert a value from the iterator to kwargs for an MDAEvent."""

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """

    def should_skip(self, kwargs: dict[str, IterItem]) -> bool:
        """Return True if the event should be skipped."""
        return False


# ------- concrete base class/mixin that implements the above protocol -------


class AxisIterableBase(BaseModel):
    axis_key: ClassVar[str]

    def create_event_kwargs(self, val: T) -> MDAEventDict:
        """Convert a value from the iterator to kwargs for an MDAEvent."""
        raise NotImplementedError

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """
        if isinstance(self, Sized):
            return len(self)
        raise NotImplementedError

    def should_skip(self, kwargs: dict[str, IterItem]) -> bool:
        return False
