from dataclasses import dataclass
from typing import Any, get_origin

import pydantic
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

pydantic_version = tuple(int(x) for x in pydantic.VERSION.split(".")[:2])
if pydantic_version >= (2, 11):
    json_input: dict = {"json_schema_input_schema": core_schema.str_schema()}
else:
    json_input = {}


@dataclass(frozen=True)
class ImportableObject:
    """Pydantic schema for importable objects.

    Example usage:

    ```python
    field: Annotated[SomeClass, ImportableObject()]
    ```

    Putting this object in a field annotation will allow the field to accept any object
    that can be imported from a string path, such as `"module.submodule.ClassName"`, and
    which, when instantiated, will obey `isinstance(obj, SomeClass)`.
    """

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Return the schema for the importable object."""

        def import_python_path(value: Any) -> Any:
            """Import a Python object from a string path."""
            if isinstance(value, str):
                # If a string is provided, it should be a path to the class
                # that implements the EventBuilder protocol.
                from importlib import import_module

                parts = value.rsplit(".", 1)
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid import path: {value!r}. "
                        "Expected format: 'module.submodule.ClassName'"
                    )
                module_name, class_name = parts
                module = import_module(module_name)
                cls = getattr(module, class_name)
                if not isinstance(cls, type):
                    raise ValueError(f"Expected a class at {value!r}, but got {cls!r}.")
                value = cls()
            return value

        def get_python_path(value: Any) -> str:
            """Get a unique identifier for the event builder."""
            val_type = type(value)
            return f"{val_type.__module__}.{val_type.__qualname__}"

        origin = source_type
        try:
            isinstance(None, origin)
        except TypeError:
            origin = get_origin(origin)
            try:
                isinstance(None, origin)
            except TypeError:
                origin = object

        to_pp_ser = core_schema.plain_serializer_function_ser_schema(
            function=get_python_path
        )
        return core_schema.no_info_before_validator_function(
            function=import_python_path,
            schema=core_schema.is_instance_schema(origin),
            serialization=to_pp_ser,
            **json_input,
        )
