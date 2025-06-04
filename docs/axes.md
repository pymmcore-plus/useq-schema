# Axes

The following objects may be used to describe iteration over specific
types of dimensions.

## Channels

- Channels may be described as an iterable of [`useq.Channel`][] objects.

## Positions

- Positions may be described as an iterable of [`useq.AbsolutePosition`][] objects.
- [`useq.WellPlatePlan`][] - A builtin position plan that describes a sequence of
  acquisitions in a well plate, with a selection of wells on a multiwell plate.

## Time Plans

Ways to describe a temporal acquisition sequence.

- [`useq.TIntervalDuration`][] - A time plan that describes a sequence of
  acquisitions with a fixed interval and duration.
- [`useq.TIntervalLoops`][] - A time plan that describes a sequence of
  acquisitions with a fixed interval and a number of loops.
- [`useq.TDurationLoops`][] - A time plan that describes a sequence of
  acquisitions with a fixed duration and a number of loops.
- [`useq.MultiPhaseTimePlan`][] - A time plan that describes a sequence of
  acquisitions with multiple phases, each with its own interval and duration.

## Z Plans

Ways to describe a z-stack acquisition sequence.

- [`useq.ZTopBottom`][] - A z plan that describes a sequence of
  acquisitions from the top to the bottom of the sample.
- [`useq.ZAboveBelow`][] - A z plan that describes a sequence of
  acquisitions above and below a reference point.
- [`useq.ZAbsolutePositions`][] - A z plan that describes a sequence of
  acquisitions at absolute positions in the z dimension.
- [`useq.ZRangeAround`][] - A z plan that describes a sequence of
  acquisitions around a reference point in the z dimension.
- [`useq.ZRelativePositions`][] - A z plan that describes a sequence of
  acquisitions at relative positions in the z dimension.

## Grid Plans

Ways to describe a grid acquisition sequence.

- [`useq.GridRowsColumns`][] - A grid plan that describes a sequence of
  acquisitions in a grid with a specified number of rows and columns.
- [`useq.GridWidthHeight`][] - A grid plan that describes a sequence of
  acquisitions in a grid with specified width and height.
- [`useq.GridFromEdges`][] - A grid plan that describes a sequence of
  acquisitions in a grid defined by edges.
- [`useq.RandomPoints`][] - A grid plan that describes a sequence of
  acquisitions at random points in the grid.

## Enums

- [`useq._grid.RelativeTo`][] - Where a grid is relative to.
- [`useq._grid.OrderMode`][] - The order in which acquisitions are made in a grid.
- [`useq._grid.Shape`][] - The shape of the grid.
