from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import TypeAlias

    from useq.new._multidim_seq import MultiDimSequence

    AxisKey: TypeAlias = str
    Value: TypeAlias = Any
    Index: TypeAlias = int
    AxesIndex: TypeAlias = dict[AxisKey, tuple[Index, Value, "AxisIterable"]]

V = TypeVar("V", covariant=True)


@runtime_checkable
class AxisIterable(Protocol[V]):
    @property
    @abstractmethod
    def axis_key(self) -> str:
        """A string id representing the axis."""

    @abstractmethod
    def __iter__(self) -> Iterator[V | MultiDimSequence]:
        """Iterate over the axis.

        If a value needs to declare sub-axes, yield a nested MultiDimSequence.
        """

    def should_skip(self, prefix: AxesIndex) -> bool:
        """Return True if this axis wants to skip the combination.

        Default implementation returns False.
        """
        return False
