from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, MutableSequence, cast

import pydantic.version
from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

PYDANTIC2 = pydantic.version.VERSION.startswith("2")

__all__ = ["model_validator", "field_validator"]

if PYDANTIC2:
    from pydantic import functional_validators, model_validator

    try:
        from pydantic_extra_types.color import Color as Color
    except ImportError:
        from pydantic.color import Color as Color

    def model_fields(obj: BaseModel | type[BaseModel]) -> dict[str, FieldInfo]:
        return obj.model_fields

    def field_regex(obj: type[BaseModel], field_name: str) -> str | None:
        field_info = obj.model_fields[field_name]
        if field_info.json_schema_extra:
            return field_info.json_schema_extra.get("pattern")
        return None

    def fields_set(obj: BaseModel) -> set[str]:
        return obj.model_fields_set

    def field_validator(*args: Any, **kwargs: Any) -> Callable[[Callable], Callable]:
        kwargs.pop("always", None)
        return functional_validators.field_validator(*args, **kwargs)

    def field_type(field: FieldInfo) -> Any:
        return field.annotation

    def get_default(f: FieldInfo) -> Any:
        return f.get_default(call_default_factory=True)

    def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.model_dump(**kwargs)

    def model_rebuild(obj: type[BaseModel], **kwargs: Any) -> BaseModel:
        return obj.model_rebuild(_types_namespace=kwargs)

else:
    from pydantic import root_validator, validator  # type: ignore
    from pydantic.color import Color as Color  # type: ignore [no-redef]

    def model_fields(  # type: ignore
        obj: BaseModel | type[BaseModel],
    ) -> dict[str, Any]:
        return obj.__fields__  # type: ignore

    def field_type(field: Any) -> Any:  # type: ignore
        return field.type_

    def field_regex(obj: type[BaseModel], field_name: str) -> str | None:
        field = obj.__fields__[field_name]  # type: ignore
        return cast(str, field.field_info.regex)

    def fields_set(obj: BaseModel) -> set[str]:
        return obj.__fields_set__

    def model_validator(**kwargs: Any) -> Callable[[Callable], Callable]:  # type: ignore  # noqa
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True
        return root_validator(**kwargs)

    def field_validator(*fields: str, **kwargs: Any) -> Callable[[Callable], Callable]:  # type: ignore  # noqa
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True
            return validator(*fields, **kwargs)
        return validator(*fields, **kwargs)

    def get_default(f: Any) -> Any:  # type: ignore
        return f.get_default()

    def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.dict(**kwargs)

    def model_rebuild(obj: type[type][BaseModel], **kwargs: Any) -> BaseModel:
        obj.update_forward_refs(**kwargs)


def update_set_fields(self: BaseModel) -> None:
    """Update set fields with populated mutable sequences.

    Because pydantic isn't aware of mutations to sequences, it can't tell when
    a field has been "set" by mutating a sequence.  This method updates the
    self.__fields_set__ attribute to reflect that.  We assume that if an attribute
    is not None, and is not equal to the default value, then it has been set.
    """
    for field_name, field in model_fields(self).items():
        current = getattr(self, field_name)
        if not current:
            continue
        if current != get_default(field):
            fields_set(self).add(field_name)
        if isinstance(current, BaseModel):
            update_set_fields(current)
        if isinstance(current, MutableSequence):
            for item in current:
                if isinstance(item, BaseModel):
                    update_set_fields(item)
