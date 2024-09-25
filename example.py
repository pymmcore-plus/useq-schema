import abc
from dataclasses import dataclass
from itertools import count, islice, product
from typing import Iterable, Iterator, TypeVar, cast

T = TypeVar("T")


class AxisIterator(Iterable[T]):
    INFINITE = -1

    @property
    @abc.abstractmethod
    def axis_key(self) -> str:
        """A string id representing the axis."""

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """
        return self.INFINITE


class TimePlan(AxisIterator[float]):
    axis_key = "t"

    def __iter__(self) -> Iterator[float]:
        yield 1.0
        yield 2.0

    def length(self) -> int:
        return 2


class ZPlan(AxisIterator[int]):
    def __init__(self, stop: int | None = None) -> None:
        self._stop = stop

    axis_key = "z"

    def __iter__(self) -> Iterator[int]:
        if self._stop is not None:
            return iter(range(self._stop))
        return count()

    def length(self) -> int:
        return self._stop or self.INFINITE


@dataclass
class MySequence:
    axes: tuple[AxisIterator, ...]
    order: tuple[str, ...]
    chunk_size = 1000

    @property
    def is_infinite(self) -> bool:
        """Return `True` if the sequence is infinite."""
        return any(ax.length() == ax.INFINITE for ax in self.axes)

    def _enumerate_ax(
        self, key: str, ax: Iterable[T], start: int = 0
    ) -> Iterable[tuple[str, int, T]]:
        """Return the key for an enumerated axis."""
        for idx, val in enumerate(ax, start):
            yield key, idx, val

    def __iter__(self) -> Iterator[tuple[str, T]]:
        """Iterate over the sequence."""
        ax_map = {ax.axis_key: ax for ax in self.axes}
        sorted_axes = [ax_map[key] for key in self.order]
        if not self.is_infinite:
            iterators = (self._enumerate_ax(ax.axis_key, ax) for ax in sorted_axes)
            yield from product(*iterators)
        else:
            idx = 0
            while True:
                yield from self._iter_infinite_slice(sorted_axes, idx, self.chunk_size)
                idx += self.chunk_size

    def _iter_infinite_slice(
        self, sorted_axes: list[AxisIterator], start: int, chunk_size: int
    ) -> Iterator[tuple[str, T]]:
        """Iterate over a slice of an infinite sequence."""
        iterators = []
        for ax in sorted_axes:
            if ax.length() is not ax.INFINITE:
                iterator, begin = cast("Iterable", ax), 0
            else:
                # use islice to avoid calling product with infinite iterators
                iterator, begin = islice(ax, start, start + chunk_size), start
            iterators.append(self._enumerate_ax(ax.axis_key, iterator, begin))

        return product(*iterators)
