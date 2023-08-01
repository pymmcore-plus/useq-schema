from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

import pydantic.version
from pydantic import BaseModel

PYDANTIC2 = pydantic.version.VERSION.startswith("2")
BM = TypeVar("BM", bound=BaseModel)

__all__ = [
    "PYDANTIC2",
    "model_validator",
    "field_validator",
    "field_serializer",
    "model_serializer",
]


if PYDANTIC2:
    from pydantic import (
        field_serializer,
        functional_validators,
        model_serializer,
        model_validator,
    )

    def field_validator(*args: Any, **kwargs: Any) -> Callable[[Callable], Callable]:
        kwargs.pop("always", None)
        kwargs.pop("allow_reuse", None)
        return functional_validators.field_validator(*args, **kwargs)

    def pydantic_1_style_root_dict(cls: type[BM], values: BM) -> dict:
        # deal with the fact that in pydantic1
        # root_validator after returned a dict of {field_name -> validated_value}
        # but in pydantic2 it returns the complete validated model instance
        return {k: getattr(values, k) for k in cls.model_fields}

    FROZEN = {"frozen": True}

elif not TYPE_CHECKING:
    from pydantic import root_validator, validator

    def model_validator(**kwargs: Any) -> Callable[[Callable], Callable]:
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True  # pragma: no cover
        return root_validator(**kwargs)

    def field_validator(*fields: str, **kwargs: Any) -> Callable[[Callable], Callable]:
        if kwargs.pop("mode", None) == "before":
            kwargs["pre"] = True
        return validator(*fields, **kwargs)

    def pydantic_1_style_root_dict(cls: type[BM], values: dict) -> dict:
        return values

    def model_serializer(**kwargs):
        return lambda f: f  # pragma: no cover

    def field_serializer(*args, **kwargs):
        return lambda f: f  # pragma: no cover

    FROZEN = {"allow_mutation": False}
