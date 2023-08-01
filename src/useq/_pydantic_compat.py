from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pydantic.version
from pydantic import BaseModel

BM = TypeVar("BM", bound=BaseModel)

__all__ = ["field_serializer", "model_serializer"]


if pydantic.version.VERSION.startswith("2"):
    from pydantic import field_serializer, model_serializer

    def pydantic_1_style_root_dict(cls: type[BM], values: BM) -> dict:
        # deal with the fact that in pydantic1
        # root_validator after returned a dict of {field_name -> validated_value}
        # but in pydantic2 it returns the complete validated model instance
        return {k: getattr(values, k) for k in cls.model_fields}

    FROZEN = {"frozen": True}

elif not TYPE_CHECKING:

    def pydantic_1_style_root_dict(cls: type[BM], values: dict) -> dict:
        return values

    def model_serializer(**kwargs):
        return lambda f: f  # pragma: no cover

    def field_serializer(*args, **kwargs):
        return lambda f: f  # pragma: no cover

    FROZEN = {"allow_mutation": False}
