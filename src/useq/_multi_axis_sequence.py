from collections.abc import Iterable, Iterator, Sequence
from itertools import islice, product
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    cast,
)

from pydantic import ConfigDict, field_validator

from useq._axis_iterable import AxisIterable
from useq._base_model import UseqModel
from useq._mda_event import MDAEvent

if TYPE_CHECKING:
    from useq._iter_sequence import MDAEventDict

T = TypeVar("T")

INFINITE = NotImplemented


class MultiDimSequence(UseqModel):
    """A multi-dimensional sequence of events.

    Attributes
    ----------
    axes : Tuple[AxisIterable, ...]
        The individual axes to iterate over.
    axis_order: tuple[str, ...] | None
        An explicit order in which to iterate over the axes.
        If `None`, axes are iterated in the order provided in the `axes` attribute.
        Note that this may also be manually passed as an argument to the `iterate`
        method.
    chunk_size: int
        For infinite sequences, the number of events to generate at a time.
    """

    axes: tuple[AxisIterable, ...] = ()
    # if none, axes are used in order provided
    axis_order: tuple[str, ...] | None = None
    chunk_size: int = 10

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("axes", mode="after")
    def _validate_axes(cls, v: tuple[AxisIterable, ...]) -> tuple[AxisIterable, ...]:
        keys = [x.axis_key for x in v]
        if not len(keys) == len(set(keys)):
            dupes = {k for k in keys if keys.count(k) > 1}
            raise ValueError(
                f"The following axis keys appeared more than once: {dupes}"
            )
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
        _axis_order = axis_order or self.axis_order or list(ax_map)
        if unknown_keys := set(_axis_order) - set(ax_map):
            raise KeyError(
                f"Unknown axis key(s): {unknown_keys!r}. Recognized axes: {set(ax_map)}"
            )
        sorted_axes = [ax_map[key] for key in _axis_order]
        if not sorted_axes:
            return

        for item in self._iter_inner(sorted_axes):
            event_index = {}
            values = {}
            for axis_key, idx, value in item:
                event_index[axis_key] = idx
                values[axis_key] = ax_map[axis_key].create_event_kwargs(value)
            # values now looks something like this:
            # {
            #     "t": {"min_start_time": 0.0},
            #     "p": {"x_pos": 0.0, "y_pos": 0.0},
            #     "c": {"channel": {"config": "DAPI", "group": "Channel"}},
            #     "z": {"z_pos_rel": -2.0},
            # }

            # fixme: i think this needs to be smarter...
            merged_kwargs: MDAEventDict = {}
            for axis_key, kwargs in values.items():
                merged_kwargs.update(kwargs)
            merged_kwargs["index"] = event_index
            event = MDAEvent(**merged_kwargs)

            if not any(ax_type.should_skip(event) for ax_type in ax_map.values()):
                yield event

    def _iter_inner(
        self, sorted_axes: Sequence[AxisIterable]
    ) -> Iterable[tuple[str, int, Any]]:
        """Iterate over the sequence.

        Yield tuples of (axis_key, index, value) for each axis.
        """
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
            if ax.length() is not INFINITE:
                iterator, begin = cast("Iterable", ax), 0
            else:
                # use islice to avoid calling product with infinite iterators
                iterator, begin = islice(ax, start, start + chunk_size), start
            iterators.append(self._enumerate_ax(ax.axis_key, iterator, begin))

        yield from product(*iterators)
