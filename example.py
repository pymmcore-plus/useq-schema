import abc
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from itertools import count, islice, product
from typing import TypeVar, cast

from useq._mda_event import MDAEvent

T = TypeVar("T")


class AxisIterator(Iterable[T]):
    INFINITE = -1

    @property
    @abc.abstractmethod
    def axis_key(self) -> str:
        """A string id representing the axis."""

    def __iter__(self) -> Iterator[T]:
        """Iterate over the axis."""

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """
        return self.INFINITE

    @abc.abstractmethod
    def create_event_kwargs(cls, val: T) -> dict: ...

    def should_skip(cls, kwargs: dict) -> bool:
        return False


class TimePlan(AxisIterator[float]):
    def __init__(self, tpoints: Sequence[float]) -> None:
        self._tpoints = tpoints

    axis_key = "t"

    def __iter__(self) -> Iterator[float]:
        yield from self._tpoints

    def length(self) -> int:
        return len(self._tpoints)

    def create_event_kwargs(cls, val: float) -> dict:
        return {"min_start_time": val}


class ZPlan(AxisIterator[int]):
    def __init__(self, stop: int | None = None) -> None:
        self._stop = stop
        self.acquire_every = 2

    axis_key = "z"

    def __iter__(self) -> Iterator[int]:
        if self._stop is not None:
            return iter(range(self._stop))
        return count()

    def length(self) -> int:
        return self._stop or self.INFINITE

    def create_event_kwargs(cls, val: int) -> dict:
        return {"z_pos": val}

    def should_skip(self, event: dict) -> bool:
        index = event["index"]
        if "t" in index and index["t"] % self.acquire_every:
            return True
        return False


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

    def __iter__(self) -> MDAEvent:
        ax_map: dict[str, type[AxisIterator]] = {ax.axis_key: ax for ax in self.axes}
        for item in self._iter_inner():
            event: dict = {"index": {}}
            for axis_key, index, value in item:
                ax_type = ax_map[axis_key]
                event["index"][axis_key] = index
                event.update(ax_type.create_event_kwargs(value))

            if not any(ax_type.should_skip(event) for ax_type in ax_map.values()):
                yield MDAEvent(**event)

    def _iter_inner(self) -> Iterator[tuple[str, int, T]]:
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


if __name__ == "__main__":
    seq = MySequence(axes=(TimePlan((0, 1, 2, 3, 4)), ZPlan(3)), order=("t", "z"))
    if seq.is_infinite:
        print("Infinite sequence")
        sys.exit(0)
    for event in seq:
        print(event)
