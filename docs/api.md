# API

In addition to declaring a schema (which is intended to be language agnostic),
`useq-schema` offers a python API for working with
[`MDASequence`][useq.MDASequence] and [`MDAEvent`][useq.MDAEvent] objects.

::: useq.MDASequence
    options:
        show_signature: true
        show_signature_annotations: true
        members:
            - replace
            - shape
            - sizes
            - used_axes
            - iter_axis
            - iter_events
            - to_pycromanager
            - __eq__
            - __len__
            - __iter__


::: useq._mda_sequence.iter_sequence
    options:
        show_source: true
        show_signature: true
        show_signature_annotations: true
