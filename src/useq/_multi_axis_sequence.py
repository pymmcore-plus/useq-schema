from collections.abc import Iterable, Iterator, Sequence
from http.client import VARIANT_ALSO_NEGOTIATES
from itertools import islice, product
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    cast,
)

from pydantic import ConfigDict, field_validator

from useq._axis_iterable import AxisIterable, IterItem
from useq._base_model import UseqModel
from useq._mda_event import MDAEvent
from useq._position import Position
from useq._utils import Axis

if TYPE_CHECKING:
    from useq._iter_sequence import MDAEventDict

T = TypeVar("T")

INFINITE = float("inf")


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
    ) -> Iterable[tuple[str, int, T, Iterable[T]]]:
        """Return the key for an enumerated axis."""
        for idx, val in enumerate(ax, start):
            yield key, idx, val, ax

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore [override]
        return self.iterate()

    def iterate(
        self,
        axis_order: Sequence[str] | None = None,
        _iter_items: tuple[IterItem, ...] = (),
        _last_t_idx: int = -1,
    ) -> Iterator[MDAEvent]:
        ax_map: dict[str, AxisIterable] = {ax.axis_key: ax for ax in self.axes}
        _axis_order = axis_order or self.axis_order or list(ax_map)
        if unknown_keys := set(_axis_order) - set(ax_map):
            raise KeyError(
                f"Unknown axis key(s): {unknown_keys!r}. Recognized axes: {set(ax_map)}"
            )
        sorted_axes = [ax_map[key] for key in _axis_order]
        if not sorted_axes:
            return

        for axis_items in self._iter_inner(sorted_axes):
            event_index = {}
            iter_items: dict[str, IterItem] = {}

            for axis_key, idx, value, iterable in axis_items:
                iter_items[axis_key] = IterItem(axis_key, idx, value, iterable)
                event_index[axis_key] = idx

            if any(ax_type.should_skip(iter_items) for ax_type in ax_map.values()):
                continue

            item_values = tuple(iter_items.values())z
            event = self._build_event(_iter_items + item_values)

            for item in item_values:
                if isinstance(pos := item.value, Position) and isinstance(
                    seq := getattr(pos, "sequence", None), MultiDimSequence
                ):
                    yield from seq.iterate(
                        _iter_items=item_values, _last_t_idx=_last_t_idx
                    )
                    break  # Don't yield a "parent" event if sub-sequence is used
            else:
                if event.index.get(Axis.TIME) == 0 and _last_t_idx != 0:
                    object.__setattr__(event, "reset_event_timer", True)
                yield event
                _last_t_idx = event.index.get(Axis.TIME, _last_t_idx)

        # breakpoint()
        # if pos.x is not None:
        #     xpos = sub_event.x_pos or 0
        #     object.__setattr__(sub_event, "x_pos", xpos + pos.x)
        # if pos.y is not None:
        #     ypos = sub_event.y_pos or 0
        #     object.__setattr__(sub_event, "y_pos", ypos + pos.y)
        # if pos.z is not None:
        #     zpos = sub_event.z_pos or 0
        #     object.__setattr__(sub_event, "z_pos", zpos + pos.z)
        # kwargs = sub_event.model_dump(mode="python", exclude_none=True)
        # kwargs["index"] = {**event_index, **sub_event.index}
        # kwargs["metadata"] = {**event.metadata, **sub_event.metadata}

        # sub_event = event.replace(**kwargs)

    def _build_event(self, iter_items: Sequence[IterItem]) -> MDAEvent:
        iter_items = list({i[0]: i for i in iter_items}.values())
        event_dicts: list[MDAEventDict] = []
        # values will look something like this:
        # [
        #     {"min_start_time": 0.0},
        #     {"x_pos": 0.0, "y_pos": 0.0, "z_pos": 0.0},
        #     {"channel": {"config": "DAPI", "group": "Channel"}},
        #     {"z_pos_rel": -2.0},
        # ]
        abs_pos: dict[str, float] = {}
        index: dict[str, int] = {}
        for item in iter_items:
            kwargs = item.axis_iterable.create_event_kwargs(item.value)
            event_dicts.append(kwargs)
            index[item.axis_key] = item.axis_index
            for key, val in kwargs.items():
                if key.endswith("_pos"):
                    if key in abs_pos and abs_pos[key] != val:
                        raise ValueError(
                            "Conflicting absolute position values for "
                            f"{key}: {abs_pos[key]} and {val}"
                        )
                    abs_pos[key] = val

        # add relative positions
        for kwargs in event_dicts:
            for key, val in kwargs.items():
                if key.endswith("_pos_rel"):
                    abs_key = key.replace("_rel", "")
                    abs_pos.setdefault(abs_key, 0.0)
                    abs_pos[abs_key] += val

        # now merge all the kwargs into a single dict
        event_kwargs: MDAEventDict = {}
        for kwargs in event_dicts:
            event_kwargs.update(kwargs)
        event_kwargs.update(abs_pos)
        event_kwargs["index"] = index
        return MDAEvent.model_construct(**event_kwargs)

    def _iter_inner(
        self, sorted_axes: Sequence[AxisIterable]
    ) -> Iterable[tuple[tuple[str, int, Any, AxisIterable], ...]]:
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
    ) -> Iterable[tuple[tuple[str, int, Any, AxisIterable], ...]]:
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
