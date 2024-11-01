from itertools import islice, product
from typing import Any, Iterable, Iterator, Sequence, TypeVar, cast

from pydantic import ConfigDict, field_validator

from useq._axis_iterator import INFINITE, AxisIterable
from useq._base_model import UseqModel
from useq._mda_event import MDAEvent

T = TypeVar("T")


class MultiDimSequence(UseqModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    axes: tuple[AxisIterable, ...] = ()
    # if none, axes are used in order provided
    axis_order: tuple[str, ...] | None = None
    chunk_size: int = 1000

    @field_validator("axes", mode="after")
    def _validate_axes(cls, v: tuple[AxisIterable, ...]) -> tuple[AxisIterable, ...]:
        keys = [x.axis_key for x in v]
        if not len(keys) == len(set(keys)):
            raise ValueError("Duplicate axis keys detected.")
        return v

    @field_validator("axis_order", mode="before")
    @classmethod
    def _validate_axis_order(cls, v: Any) -> tuple[str, ...]:
        if not isinstance(v, Iterable):
            raise ValueError(f"axis_order must be iterable, got {type(v)}")
        order = tuple(str(x).lower() for x in v)
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order

    @property
    def is_infinite(self) -> bool:
        """Return `True` if the sequence is infinite."""
        return any(ax.length() is INFINITE for ax in self.axes)

    def _enumerate_ax(
        self, key: str, ax: Iterable[T], start: int = 0
    ) -> Iterable[tuple[str, int, T]]:
        """Return the key for an enumerated axis."""
        for idx, val in enumerate(ax, start):
            yield key, idx, val

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore [override]
        return self.iterate()

    def iterate(self, axis_order: Sequence[str] | None = None) -> Iterator[MDAEvent]:
        ax_map: dict[str, AxisIterable] = {ax.axis_key: ax for ax in self.axes}
        for item in self._iter_inner(axis_order):
            event: dict = {"index": {}}
            for axis_key, index, value in item:
                ax_type = ax_map[axis_key]
                event["index"][axis_key] = index
                event.update(ax_type.create_event_kwargs(value))

            if not any(ax_type.should_skip(event) for ax_type in ax_map.values()):
                yield MDAEvent(**event)

    def _iter_inner(
        self, axis_order: Sequence[str] | None = None
    ) -> Iterable[tuple[str, int, Any]]:
        """Iterate over the sequence."""
        ax_map = {ax.axis_key: ax for ax in self.axes}
        _axis_order = axis_order or self.axis_order or list(ax_map)
        if unknown_keys := set(_axis_order) - set(ax_map):
            raise KeyError(
                f"Unknown axis key(s): {unknown_keys!r}. Recognized axes: {set(ax_map)}"
            )
        sorted_axes = [ax_map[key] for key in _axis_order]
        if not sorted_axes:
            return
        if not self.is_infinite:
            iterators = (self._enumerate_ax(ax.axis_key, ax) for ax in sorted_axes)
            yield from product(*iterators)
        else:
            idx = 0
            while True:
                yield from self._iter_infinite_slice(sorted_axes, idx, self.chunk_size)
                idx += self.chunk_size

    def _iter_infinite_slice(
        self, sorted_axes: list[AxisIterable], start: int, chunk_size: int
    ) -> Iterable[tuple[str, int, Any]]:
        """Iterate over a slice of an infinite sequence."""
        iterators = []
        for ax in sorted_axes:
            if ax.length() is not ax.INFINITE:
                iterator, begin = cast("Iterable", ax), 0
            else:
                # use islice to avoid calling product with infinite iterators
                iterator, begin = islice(ax, start, start + chunk_size), start
            iterators.append(self._enumerate_ax(ax.axis_key, iterator, begin))

        yield from product(*iterators)
