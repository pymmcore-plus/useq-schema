from typing import TYPE_CHECKING

import pydantic.version

__all__ = ["field_serializer", "model_serializer"]


if pydantic.version.VERSION.startswith("2"):
    from pydantic import field_serializer, model_serializer

    FROZEN = {"frozen": True}

elif not TYPE_CHECKING:

    def model_serializer(**kwargs):
        return lambda f: f  # pragma: no cover

    def field_serializer(*args, **kwargs):
        return lambda f: f  # pragma: no cover

    FROZEN = {"allow_mutation": False}
