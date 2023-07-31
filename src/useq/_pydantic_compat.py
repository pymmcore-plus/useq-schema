from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

import pydantic.version
from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic import field_serializer, model_serializer
    from pydantic.fields import FieldInfo

PYDANTIC2 = pydantic.version.VERSION.startswith("2")

__all__ = ["model_validator", "field_validator", "field_serializer", "model_serializer"]

BM = TypeVar("BM", bound=BaseModel)

if PYDANTIC2:
    from pydantic import field_serializer as field_serializer  # noqa
    from pydantic import functional_validators, model_validator
    from pydantic import model_serializer as model_serializer  # noqa

    def model_fields(obj: BaseModel | type[BaseModel]) -> dict[str, FieldInfo]:
        return obj.model_fields

    def field_validator(*args: Any, **kwargs: Any) -> Callable[[Callable], Callable]:
        kwargs.pop("always", None)
        kwargs.pop("allow_reuse", None)
        return functional_validators.field_validator(*args, **kwargs)

    def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.model_dump(**kwargs)

    def model_dump_json(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.model_dump_json(**kwargs)

    def model_rebuild(obj: type[BaseModel], **kwargs: Any) -> bool | None:
        return obj.model_rebuild(_types_namespace=kwargs)

    def model_construct(obj: type[BM], **kwargs: Any) -> BM:
        return obj.model_construct(**kwargs)

    def pydantic_1_style_root_dict(cls: type[BM], values: BM) -> dict:
        # deal with the fact that in pydantic1
        # root_validator after returned a dict of {field_name -> validated_value}
        # but in pydantic2 it returns the complete validated model instance
        return {k: getattr(values, k) for k in cls.model_fields}

    FROZEN = {"frozen": True}

else:
    from pydantic import root_validator, validator  # type: ignore

    def model_fields(  # type: ignore
        obj: BaseModel | type[BaseModel],
    ) -> dict[str, Any]:
        return obj.__fields__  # type: ignore

    def model_validator(**kwargs: Any) -> Callable[[Callable], Callable]:  # type: ignore  # noqa
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True
        return root_validator(**kwargs)

    def field_validator(*fields: str, **kwargs: Any) -> Callable[[Callable], Callable]:  # type: ignore  # noqa
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True
            return validator(*fields, **kwargs)
        return validator(*fields, **kwargs)

    def model_dump(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.dict(**kwargs)

    def model_dump_json(obj: BaseModel, **kwargs: Any) -> dict[str, Any]:
        return obj.json(**kwargs)

    def model_rebuild(obj: type[BM], **kwargs: Any) -> BaseModel:
        obj.update_forward_refs(**kwargs)

    def model_construct(obj: type[BM], **kwargs: Any) -> BM:
        return obj.construct(**kwargs)

    def pydantic_1_style_root_dict(cls: type[BM], values: dict) -> dict:
        return values

    def model_serializer(**kwargs):
        return lambda f: f

    def field_serializer(*args, **kwargs):
        return lambda f: f

    FROZEN = {"allow_mutation": False}
