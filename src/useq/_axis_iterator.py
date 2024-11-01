from __future__ import annotations

import abc
from typing import (
    TYPE_CHECKING,
    Iterator,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from useq._iter_sequence import MDAEventDict

T = TypeVar("T")

INFINITE = NotImplemented


@runtime_checkable
class AxisIterable(Protocol):
    @property
    @abc.abstractmethod
    def axis_key(self) -> str:
        """A string id representing the axis."""

    @abc.abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Iterate over the axis."""

    @abc.abstractmethod
    def create_event_kwargs(cls, val: T) -> MDAEventDict:
        """Convert a value from the iterator to kwargs for an MDAEvent."""

    # def length(self) -> int:
    #     """Return the number of axis values.

    #     If the axis is infinite, return -1.
    #     """
    #     return INFINITE

    # def should_skip(cls, kwargs: dict) -> bool:
    #     return False
