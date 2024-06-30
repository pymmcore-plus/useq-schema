# useq-schema

[![License](https://img.shields.io/pypi/l/useq-schema.svg?color=green)](https://github.com/pymmcore-plus/useq-schema/raw/main/LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/useq-schema)](https://pypi.org/project/useq-schema)
[![PyPI](https://img.shields.io/pypi/v/useq-schema.svg?color=green)](https://pypi.org/project/useq-schema)
[![Conda](https://img.shields.io/conda/vn/conda-forge/useq-schema)](https://anaconda.org/conda-forge/useq-schema)
[![tests](https://github.com/pymmcore-plus/useq-schema/actions/workflows/test_and_deploy.yml/badge.svg)](https://github.com/pymmcore-plus/useq-schema/actions/workflows/test_and_deploy.yml)
[![docs](https://github.com/pymmcore-plus/useq-schema/actions/workflows/docs.yml/badge.svg)](https://pymmcore-plus.github.io/useq-schema/)
[![codecov](https://codecov.io/gh/pymmcore-plus/useq-schema/branch/main/graph/badge.svg)](https://codecov.io/gh/pymmcore-plus/useq-schema)

*An implementation agnostic schema for describing a sequence of events during a
multi-dimensional imaging acquisition.*

**Documentation: <https://pymmcore-plus.github.io/useq-schema/>**

The goal of this repo is to provide a specification (and some python utilities)
for generating event objects that can be consumed by microscope acquisition
engines.  The *hope* is that this will encourage interoperability between
various efforts to drive automated image acquisition.

The schema *tries* to remain agnostic to the specific acquisition engine, though
it was designed around the needs of Micro-Manager. One hope is to solicit
feedback from interested parties regarding limitations and/or potential
extensions to the schema.  Similarly, while the "ideal" schema will support
arbitrary dimensions (i.e. more than the conventional position, time, channel,
z, ...), it also hard to avoid hard-coding some assumptions about dimensionality
in certain places.  

Any and all feedback is welcome!  Please get in touch if you have any thoughts.

## `MDAEvent`

The primary "event" object is `useq.MDAEvent`.  This represents a single event
that a microscope should perform, including preparation of the hardware, and
execution of the event (such as an image acquisition).  This is the simpler,
but more important of the two objects.  Downstream libraries that aim to support
useq schema should support driving hardware based on an `Iterable[MDAEvent]`.

- For [micro-manager](https://github.com/micro-manager/micro-manager), this
  object is most similar (though not *that* similar) to the events generated by
  [`generate-acq-sequence`](https://github.com/micro-manager/micro-manager/blob/2b0f51a2f916112d39c6135ad35a112065f8d58d/acqEngine/src/main/clj/org/micromanager/sequence_generator.clj#L410)
  in the clojure acquisition engine.
- For [pycro-manager](https://github.com/micro-manager/pycro-manager), this
  object is similar to an individual [acquisition event
  `dict`](https://pycro-manager.readthedocs.io/en/latest/apis.html#acquisition-event-specification)
  generated by
  [`multi_d_acquisition_events`](https://github.com/micro-manager/pycro-manager/blob/63cf209a8907fd23932ee9f8016cb6a2b61b45aa/pycromanager/acquire.py#L605),
  (and, `useq` provides a `to_pycromanager()` method that converts an `MDAEvent` into a
  single pycro-manager event dict)
- *your object here?...*

See [`useq.MDAEvent` documentation](https://pymmcore-plus.github.io/useq-schema/schema/event/)
for more details.

> **Note:** `useq-schema` uses [`pydantic`](https://pydantic-docs.helpmanual.io/) to
> define models, so you can retrieve the [json schema](https://json-schema.org/)
> for the `MDAEvent` object with `MDAEvent.model_json_schema()`

## `MDASequence`

`useq.MDASequence` is a declarative representation of an entire experiment.  It
represents a sequence of events (as might be generated by the multidimensional
acquisition GUI in most microscope software).  It is composed of ["plans" for
each axis in the
experiment](https://pymmcore-plus.github.io/useq-schema/schema/axes/) (such as a
Time Plan, a Z Plan, a list of channels and positions, etc.).  A
`useq.MDASequence` object is itself iterable, and yields `MDAEvent` objects.

- For [micro-manager](https://github.com/micro-manager/micro-manager), this
  object is most similar to
  [`org.micromanager.acquisition.SequenceSettings`](https://github.com/micro-manager/micro-manager/blob/2b0f51a2f916112d39c6135ad35a112065f8d58d/mmstudio/src/main/java/org/micromanager/acquisition/SequenceSettings.java#L39),
  (generated by clicking the "Acquire!" button in the Multi-D Acquisition GUI)
- For [pycro-manager](https://github.com/micro-manager/pycro-manager), this
  object is similar to the
  [`multi_d_acquisition_events`](https://github.com/micro-manager/pycro-manager/blob/63cf209a8907fd23932ee9f8016cb6a2b61b45aa/pycromanager/acquire.py#L605)
  convenience function, (and `useq` provides a `to_pycromanager()`method that
  converts an `MDASequence` to a list of pycro-manager events)
- *your object here?...*

See [`useq.MDASequence` documentation](https://pymmcore-plus.github.io/useq-schema/schema/sequence/)
for more details.

### example `MDASequence` usage

```python
from useq import MDASequence

mda_seq = MDASequence(
    stage_positions=[(100, 100, 30), (200, 150, 35)],
    channels=["DAPI", "FITC"],
    time_plan={'interval': 1, 'loops': 20},
    z_plan={"range": 4, "step": 0.5},
    axis_order='tpcz',
)
events = list(mda_seq)

print(len(events))  # 720

print(events[:3])

# [MDAEvent(
#     channel=Channel(config='DAPI'),
#     index=mappingproxy({'t': 0, 'p': 0, 'c': 0, 'z': 0}),
#     min_start_time=0.0,
#     x_pos=100.0,
#     y_pos=100.0,
#     z_pos=28.0,
#  ),
#  MDAEvent(
#     channel=Channel(config='DAPI'),
#     index=mappingproxy({'t': 0, 'p': 0, 'c': 0, 'z': 1}),
#     min_start_time=0.0,
#     x_pos=100.0,
#     y_pos=100.0,
#     z_pos=28.5,
#  ),
#  MDAEvent(
#     channel=Channel(config='DAPI'),
#     index=mappingproxy({'t': 0, 'p': 0, 'c': 0, 'z': 2}),
#     min_start_time=0.0,
#     x_pos=100.0,
#     y_pos=100.0,
#     z_pos=29.0,
#  )]
```

serialize to yaml or json

```py
print(mda_seq.yaml())
```

```yaml
axis_order: tpcz
channels:
- config: DAPI
- config: FITC
stage_positions:
- x: 100.0
  y: 100.0
  z: 30.0
- x: 200.0
  y: 150.0
  z: 35.0
time_plan:
  interval: 0:00:01
  loops: 20
z_plan:
  range: 4.0
  step: 0.5
```

## Executing useq-schema experiments with pymmcore-plus

[pymmcore-plus](https://github.com/pymmcore-plus/pymmcore-plus) implements an
acquisition engine that can execute an `MDASequence` using
micro-manager in a pure python environment (no Java required).

```python
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()
core.loadSystemConfiguration()  # loads demo by default

core.mda.run(mda_seq)  # run the experiment

# or, construct a sequence of MDAEvents anyway you like
events = [MDAEvent(...), MDAEvent(...), ...]
core.mda.run(events)
```

See [pymmcore-plus documentation](https://pymmcore-plus.github.io/pymmcore-plus/examples/mda/) for details
