import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterator,
    Sequence,
    Union,
)

from pydantic import Field

from useq._base_model import FrozenModel
from useq._utils import parse_duration

if TYPE_CHECKING:
    from pydantic_core import CoreSchema, core_schema


# FIXME: please!!
# This is a gross amalgamation of fixes that tries to work with both pydantic1 and 2
class timedelta(datetime.timedelta):
    @classmethod
    def __get_validators__(cls) -> Generator[Callable[..., Any], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> datetime.timedelta:
        return datetime.timedelta(**v) if isinstance(v, dict) else parse_duration(v)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> "CoreSchema":
        from pydantic_core.core_schema import (
            no_info_plain_validator_function,
            plain_serializer_function_ser_schema,
        )

        serializer = plain_serializer_function_ser_schema(
            cls._serialize, when_used="json"
        )

        return no_info_plain_validator_function(cls.validate, serialization=serializer)

    @classmethod
    def _serialize(cls, v: datetime.timedelta) -> float:
        return v.total_seconds()

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: "core_schema.CoreSchema", handler: Any
    ) -> Dict[str, Any]:
        return {"type": "number", "format": "float"}


class TimePlan(FrozenModel):
    # TODO: probably needs to be implemented by engine
    prioritize_duration: bool = False  # or prioritize num frames

    def __iter__(self) -> Iterator[float]:  # type: ignore
        for td in self.deltas():
            yield td.total_seconds()

    def num_timepoints(self) -> int:
        return self.loops  # type: ignore  # TODO

    def deltas(self) -> Iterator[datetime.timedelta]:
        current = timedelta(0)
        for _ in range(self.loops):  # type: ignore  # TODO
            yield current
            current += self.interval  # type: ignore  # TODO


class TIntervalLoops(TimePlan):
    """Define temporal sequence using interval and number of loops.

    Attributes
    ----------
    interval : str | timedelta | float
        Time between frames. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    loops : int
        Number of frames.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `False`.
    """

    interval: timedelta
    loops: int = Field(..., gt=0)

    @property
    def duration(self) -> datetime.timedelta:
        return self.interval * (self.loops - 1)


class TDurationLoops(TimePlan):
    """Define temporal sequence using duration and number of loops.

    Attributes
    ----------
    duration : str | timedelta
        Total duration of sequence. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    loops : int
        Number of frames.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `False`.
    """

    duration: timedelta
    loops: int = Field(..., gt=0)

    @property
    def interval(self) -> datetime.timedelta:
        # -1 makes it so that the last loop will *occur* at duration, not *finish*
        return self.duration / (self.loops - 1)


class TIntervalDuration(TimePlan):
    """Define temporal sequence using interval and duration.

    Attributes
    ----------
    interval : str | timedelta
        Time between frames. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    duration : str | timedelta
        Total duration of sequence.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `True`.
    """

    interval: timedelta
    duration: timedelta
    prioritize_duration: bool = True

    @property
    def loops(self) -> int:
        return self.duration // self.interval + 1


SinglePhaseTimePlan = Union[TIntervalDuration, TIntervalLoops, TDurationLoops]


class MultiPhaseTimePlan(TimePlan):
    """Time sequence composed of multiple phases.

    Attributes
    ----------
    phases : Sequence[TIntervalDuration | TIntervalLoops | TDurationLoops]
        Sequence of time plans.
    """

    phases: Sequence[SinglePhaseTimePlan]

    def deltas(self) -> Iterator[datetime.timedelta]:
        accum = datetime.timedelta(0)
        yield accum
        for phase in self.phases:
            for i, td in enumerate(phase.deltas()):
                # skip the first timepoint of later phases
                if i == 0 and td == datetime.timedelta(0):
                    continue
                yield td + accum
            accum += td

    def num_timepoints(self) -> int:
        # TODO: is this correct?
        return sum(phase.loops for phase in self.phases) - 1


AnyTimePlan = Union[MultiPhaseTimePlan, SinglePhaseTimePlan]
