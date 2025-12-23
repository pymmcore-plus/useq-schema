# v2 Migration Guide

## Overview

The v2 version of `useq-schema` represents a fundamental architectural redesign
that generalizes the multi-dimensional axis iteration pattern to support
arbitrary dimensions while preserving the complex event building, nesting, and
skipping capabilities of the original implementation. This document explains the
new features, how to use and extend them, and the breaking changes from v1.

## Key Architectural Changes

### From Fixed Axes to Extensible Axis System

**v1 Approach**: Hard-coded support for specific axes (`time`, `position`,
`grid`, `channel`, `z`) with bespoke iteration logic in `_iter_sequence.py`.

**v2 Approach**: Generic, protocol-based system where any object implementing
`AxisIterable` can participate in multi-dimensional iteration.

### Core Concepts

#### 1. `AxisIterable[V]` Protocol

The foundation of v2 is the `AxisIterable` protocol, which defines how any axis
should behave.  In short, an `AxisIterable` is an object that yields values (of
any type), has an associated `axis_key`, and can contribute to event building
and skipping logic.

```python
from pydantic import BaseModel, Field
from typing import Generic, Iterator, Mapping, TypeVar
from abc import abstractmethod

V = TypeVar("V")

class AxisIterable(BaseModel, Generic[V]):
    axis_key: str  # Unique identifier for this axis

    @abstractmethod
    def __iter__(self) -> Iterator[V]:
        """Iterate over axis values"""

    def should_skip(self, prefix: AxesIndex) -> bool:
        """Return True to skip this combination"""
        return False

    def contribute_to_mda_event(
        self, value: V, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        """Contribute data to the event being built"""
        return {}
```

#### 2. `SimpleValueAxis[V]` - Basic Implementation

For simple cases where you just want to iterate over a list of values:

```python
class SimpleValueAxis(AxisIterable[V]):
    values: list[V] = Field(default_factory=list)

    def __iter__(self) -> Iterator[V | MultiAxisSequence]:
        yield from self.values
```

```python
axis = SimpleValueAxis(axis_key="z", values=[0, 1, 2, 3, 4])
for z in axis:
    print(z)  # Outputs 0, 1, 2, 3, 4
```

#### 3. `MultiAxisSequence[EventT]` - The New Sequence Container

Replaces the old `MDASequence` as the core container, but with generic event
support.  A `MultiAxisSequence` holds any number of `AxisIterable` objects,
defines their order, and manages how the values from each axis get merged into
an event.

```python
EventT = TypeVar("EventT")

class MultiAxisSequence(BaseModel, Generic[EventT]):
    axes: tuple[AxisIterable, ...] = ()
    axis_order: Optional[tuple[str, ...]] = None

    value: Any = None  # Used when this sequence is nested
    event_builder: Optional[EventBuilder[EventT]] = None
    transforms: tuple[EventTransform, ...] = ()
```

#### 4. `MDASequence`

There *is* still an `MDASequence` class in v2, which is a subclass of
`MultiAxisSequence` specialized for building `MDAEvent` objects.

```python
from useq.v2 import MDAEvent

class MDASequence(MultiAxisSequence[MDAEvent]):
    ...
```

In other words, `MultiAxisSequence` is a generic iterator over multiple
axes that can build *any* type of event, while `MDASequence` is a specific
implementation that builds `MDAEvent` objects (just like v1).

## New Features

### 1. **Arbitrary Custom Axes**

You can now define completely custom axes for any dimension:

```python
from useq import v2

# Custom axis for laser power
class LaserPowerAxis(v2.SimpleValueAxis[float]):
    axis_key: str = "laser_power"
    
    def contribute_to_mda_event(self, value: float, index: Mapping[str, int]) -> v2.MDAEvent.Kwargs:
        return {"metadata": {"laser_power": value}}

# Custom axis for temperature
class TemperatureAxis(v2.AxisIterable[float]):
    axis_key: str = "temperature"
    min_temp: float
    max_temp: float
    step: float
    
    def __iter__(self) -> Iterator[float]:
        temp = self.min_temp
        while temp <= self.max_temp:
            yield temp
            temp += self.step
            
    def contribute_to_mda_event(self, value: float, index: Mapping[str, int]) -> v2.MDAEvent.Kwargs:
        return {"metadata": {"temperature": value}}
```

### 2. **Conditional Skipping with `should_skip`**

`should_skip` method on any axis allows context-aware skipping of specific
combinations.  It receives an `AxesIndex`, which contains information on
the exact value and index being yielded by each axis in this iteration step.

```python
class FilteredChannelAxis(v2.SimpleValueAxis[v2.Channel]):
    def should_skip(self, prefix: v2.AxesIndex) -> bool:
        # Skip FITC channel for even numbered Z positions
        z_idx = prefix.get("z", (None, None, None))[0]
        current_channel = prefix.get("c", (None, None, None))[1]
        
        if z_idx is not None and z_idx % 2 == 0:
            return current_channel.config == "FITC"
        return False
```

### 3. **Hierarchical Nested Sequences**

The new system supports arbitrarily nested sequences that can override or extend
parent axes.  A `MultiAxisSequence` *itself* can have a `value`, allowing it to
be used as a yielded value from a parent axis.

In the following example, we define a sub-sequence for a specific position that
adds a temperature axis and overrides the Z plan defined in the parent sequence:

```python
from useq import v2
# Position with custom sub-sequence (uses MDASequence, which StagePositions accepts)
sub_sequence = v2.MDASequence(
    value=v2.Position(x=10, y=20),  # The value represents this position
    axes=(
        # Add temperature dimension
        v2.SimpleValueAxis(axis_key="temperature", values=[20, 25, 30]),
        # Override parent Z plan
        v2.ZRangeAround(range=2, step=0.5),
    ),
    axis_order=("temperature", "z")
)

main_sequence = v2.MDASequence(
    axes=(
        v2.TIntervalLoops(interval=1.0, loops=5),
        v2.StagePositions(values=[sub_sequence, v2.Position(x=0, y=0)]),
        v2.ZRangeAround(range=4, step=1.0),  # This gets overridden for the first position
    )
)
```

### 4. **Event Transform Pipeline**

Transforms allow you to modify events after they are built but before they are
yielded. This replaces the old hardcoded event modification logic with a
flexible, composable pipeline:

```python
from useq.v2 import KeepShutterOpenTransform, EventTransform

class CustomTransform(EventTransform[MDAEvent]):
    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        # Modify event
        if event.index.get("c") == 0:  # First channel
            event = event.model_copy(update={"exposure": 100})

        # Can return multiple events, no events, or modify the event
        return [event]

seq = v2.MDASequence(
    channels=["DAPI", "FITC"],  # Using legacy API for brevity
    transforms=(CustomTransform(), KeepShutterOpenTransform(("z",)))
)
```

#### 4.1 **Built-in Transforms**

v2 provides several built-in transforms that replicate v1 behavior.
Note: transforms are currently available from `useq.v2._transformers`:

```python
from useq.v2 import (
    AutoFocusTransform,
    KeepShutterOpenTransform,
    ResetEventTimerTransform,
)

# Shutter management - keeps shutter open across specified axes
KeepShutterOpenTransform(("z", "c"))

# Event timing - marks first frame of each timepoint for timer reset
ResetEventTimerTransform()
```

#### 4.2 **Non-Imaging Events with Transforms**

A key innovation in v2 is the ability to use transforms to insert **non-imaging
events** that don't contribute to the sequence shape. This addresses GitHub
issue [#41](https://github.com/pymmcore-plus/useq-schema/issues/41) for use
cases like laser measurements and Raman spectroscopy:

```python
class LaserMeasurementTransform(EventTransform[MDAEvent]):
    """Insert laser measurement events after BF z-stacks."""
    
    def __call__(
        self,
        event: MDAEvent,
        *,
        prev_event: MDAEvent | None,
        make_next_event: Callable[[], MDAEvent | None],
    ) -> Iterable[MDAEvent]:
        # Yield the original imaging event
        yield event
        
        # If this is the last event in a BF z-stack, add laser measurements
        if (event.channel and event.channel.config == "BF" and 
            self._is_last_z_event(event, make_next_event)):
            
            # Insert 5 laser measurement events at different points
            for i, (x_offset, y_offset) in enumerate([(0, 0), (10, 0), (0, 10), (-10, 0), (0, -10)]):
                laser_event = MDAEvent(
                    index={"t": event.index.get("t", 0), "laser": i},
                    x_pos=(event.x_pos or 0) + x_offset,
                    y_pos=(event.y_pos or 0) + y_offset,
                    action=CustomAction(type="laser_measurement", data={"laser_power": 75})
                )
                yield laser_event
    
    def _is_last_z_event(self, event: MDAEvent, make_next_event: Callable) -> bool:
        next_event = make_next_event()
        return (next_event is None or 
                next_event.channel is None or 
                next_event.channel.config != "BF")

# Usage for the GitHub issue #41 use case:
# 1. Collect BF z-stack → 2. Laser measurements → 3. GFP z-stack
seq = v2.MDASequence(
    channels=["BF", "GFP"],  
    z_plan=v2.ZRangeAround(range=2, step=0.5),
    transforms=(LaserMeasurementTransform(),)
)

# This generates:
# - BF z-stack events (contribute to shape)
# - 5 laser measurement events (inserted by transform, don't affect shape)
# - GFP z-stack events (contribute to shape)
```

### 5. **Pluggable Event Builders**

Customize how raw axis data gets converted into events:

```python
class MyCustomEvent: ...

class CustomEventBuilder(v2.EventBuilder[MyCustomEvent]):
    def __call__(
        self, axes_index: v2.AxesIndex, context: tuple[v2.MultiAxisSequence, ...]
    ) -> MyCustomEvent:
        # Build your custom event type
        return MyCustomEvent(...)

seq = v2.MultiAxisSequence(
    axes=(),
    event_builder=CustomEventBuilder()
)
```

### 6. **Infinite Axes Support**

Unlike v1, v2 supports infinite sequences:

```python
class InfiniteTimeAxis(v2.AxisIterable[float]):
    axis_key: str = "t"
    interval: float = 1.0
    
    def __iter__(self) -> Iterator[float]:
        time = 0.0
        while True:
            yield time
            time += self.interval
```

## Migration from v1 to v2

### Backward Compatibility

v2 `MDASequence` accepts the same constructor parameters as v1 through automatic
conversion:

```python
# This v1 style still works
seq = v2.MDASequence(
    time_plan={"interval": 1.0, "loops": 5},
    z_plan={"range": 4, "step": 1},
    channels=["DAPI", "FITC"],
    stage_positions=[(10, 20, 5)],
)

# Internally converted to:
seq2 = v2.MDASequence(
    axes=(
        v2.TIntervalLoops(interval=1.0, loops=5),
        v2.StagePositions(values=[v2.Position(x=10, y=20, z=5)]),
        v2.ChannelsPlan(values=[v2.Channel(config="DAPI"), v2.Channel(config="FITC")]),
        v2.ZRangeAround(range=4, step=1),
    ),
)

assert list(seq) == list(seq2)
```

### Breaking Changes

#### 1. **Event Building Architecture**

**v1**: Monolithic `_iter_sequence` function with hardcoded event building
logic.

**v2**: Separation of concerns:

- Axis iteration handled by `iterate_multi_dim_sequence`
- Event building handled by `EventBuilder`
- Event modification handled by `EventTransform` pipeline

#### 2. **Shape and Sizes Properties**

```python
from useq import MDASequence
from useq import v2

# v1
seq = MDASequence()
seq.shape  # Returns tuple of sizes
seq.sizes  # Returns mapping of axis -> size

# v2 - DEPRECATED
seq2 = v2.MDASequence()
seq2.shape  # Deprecated - raises FutureWarning
seq2.sizes  # Deprecated - raises FutureWarning

# v2 - New approach
[len(axis) for axis in seq2.axes]  # Get size per axis
seq2.is_finite()  # Check if sequence is finite
```

#### 3. **Axis Access**

```python
# v1
seq.time_plan
seq.z_plan
seq.channels
seq.stage_positions
seq.grid_plan

# v2 - Legacy properties still work but deprecated
seq2.time_plan  # Returns the time axis or None
seq2.z_plan     # Returns the z axis or None

# v2 - New approach
time_axis = next((ax for ax in seq2.axes if ax.axis_key == "t"), None)
z_axis = next((ax for ax in seq2.axes if ax.axis_key == "z"), None)

# each of which have convenience methods:
time_axis = seq2.time_plan
z_axis = seq2.z_plan
```

#### 4. **Custom Skip Logic**

**v1**: Hardcoded in `_should_skip` function within `_iter_sequence.py`

**v2**: Implemented per-axis via `should_skip` method:

```python
class CustomZAxis(v2.ZRangeAround):
    def should_skip(self, prefix: AxesIndex) -> bool:
        # Custom logic here
        return super().should_skip(prefix)
```

#### Z. **Z-Plans yield Positions, not floats**

**v1**: Z plans yielded floats representing Z positions.

**v2**: Z plans yield `Position` objects that (usually) include only z
coordinates:

## Built-in Axes in v2

All the original v1 plans are now `AxisIterable` implementations:

### Time Axes

- `TIntervalLoops`
- `TIntervalDuration`
- `TDurationLoops`
- `MultiPhaseTimePlan`

### Z Axes  

- `ZRangeAround`
- `ZTopBottom`
- `ZAboveBelow`
- `ZAbsolutePositions`
- `ZRelativePositions`

### Channel Axes

- `ChannelsPlan` (wraps list of `Channel` objects)

### Position Axes

- `StagePositions` (wraps list of `Position` objects)

### Grid Axes

- `GridRowsColumns`
- `GridFromEdges`
- `GridWidthHeight`
- `RandomPoints`

## Extension Examples

### Creating a Custom Scientific Axis

```python
class PHAxis(v2.AxisIterable[float]):
    """Axis for pH titration experiments."""
    axis_key: str = "ph"
    start_ph: float = 6.0
    end_ph: float = 8.0
    steps: int = 10
    
    def __iter__(self) -> Iterator[float]:
        step_size = (self.end_ph - self.start_ph) / (self.steps - 1)
        for i in range(self.steps):
            yield self.start_ph + i * step_size
            
    def contribute_to_mda_event(self, value: float, index: Mapping[str, int]) -> MDAEvent.Kwargs:
        return {
            "metadata": {"ph": value},
            "properties": [("pH_Controller", "target_ph", value)]
        }
    
    def should_skip(self, prefix: AxesIndex) -> bool:
        # Skip pH 7.5+ for channel index > 2
        channel_idx = prefix.get("c", (None, None, None))[0]
        ph_value = prefix.get("ph", (None, None, None))[1]
        return channel_idx is not None and channel_idx > 2 and ph_value >= 7.5
```

### Complex Nested Workflow

```python
from useq import v2

# Different regions with different imaging parameters
region1 = v2.MDASequence(
    value=v2.Position(x=0, y=0, name="Region1"),
    axes=(
        v2.ZRangeAround(range=10, step=0.2),  # High-res Z
        v2.ChannelsPlan(values=["DAPI", "FITC", "Cy3"]),  # 3 channels
    )
)

region2 = v2.MDASequence(
    value=v2.Position(x=100, y=100, name="Region2"),
    axes=(
        v2.ZRangeAround(range=20, step=0.5),  # Lower-res Z
        v2.ChannelsPlan(values=["DAPI", "Cy5"]),  # Only 2 channels
        PHAxis(start_ph=6.5, end_ph=7.5, steps=5),  # pH titration
    )
)

class CustomTransform:
    def __call__(
        self,
        event: v2.MDAEvent,
        *,
        prev_event: v2.MDAEvent | None,
        make_next_event: Callable[[], v2.MDAEvent | None],
    ) -> Iterable[v2.MDAEvent]:
        # possibly modify event... based on conditions
        yield event

main_seq = v2.MDASequence(
    axes=(
        v2.TIntervalLoops(interval=60, loops=10),  # Every minute for 10 minutes
        v2.StagePositions(values=[region1, region2]),
    ),
    transforms=(
        CustomTransform(),
        v2.KeepShutterOpenTransform(("z", "c")),  # Keep shutter open for Z and C
    )
)
```

## Performance and Design Benefits

### Separation of Concerns

- **Axis logic**: Isolated in individual `AxisIterable` implementations
- **Event building**: Centralized in `EventBuilder`
- **Event modification**: Composable `EventTransform` pipeline

### Extensibility

- Add new dimensions without modifying core code
- Custom skip logic per axis
- Pluggable event builders for different event types
- Composable transform pipeline

### Type Safety

- Generic types ensure type safety across the pipeline
- Protocol-based design enables duck typing
- Clear interfaces for each component

### Maintainability

- Individual axis implementations are easier to test and debug
- Transform pipeline is easier to reason about than monolithic logic
- Clear separation between axis iteration and event building

## Summary

useq-schema v2 transforms the library from a fixed-axis system to a fully
extensible, protocol-based architecture that supports:

- **Arbitrary custom axes** with their own iteration and contribution logic
- **Conditional skipping** per axis with full context awareness  
- **Hierarchical nesting** with axis override capabilities
- **Composable transforms** for event modification
- **Pluggable event builders** for different event types
- **Type-safe extensibility** through generic protocols

While maintaining full backward compatibility with v1 API patterns, v2 opens up
useq-schema for complex, multi-dimensional experimental workflows that were
impossible to express in the original architecture.
