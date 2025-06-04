# Primary Objects

## MDASequence

The [`useq.MDASequence`][] object is the main object used to describe a sequence of
acquisitions in a multi-dimensional space. It allows for the specification of
various parameters, including channels, positions, time points, and more.

In addition to defining the axes over which to iterate, the `MDASequence` also specifies a few event modifiers, such as an [`useq.AutoFocusPlan`][], or other state-modifying instructions such as leaving shutters open/closed, or resetting
timers

## MDAEvent

The [`useq.MDAEvent`][] object is used to describe a single event.  A `MDASequence` is
itself an `Iterable[useq.MDAEvent]`, where each event is a single acquisition, or
some other custom user-defined [`useq.Action`][].
