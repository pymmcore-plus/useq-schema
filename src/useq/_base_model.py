from __future__ import annotations

import warnings
from pathlib import Path
from types import MappingProxyType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np
from pydantic import BaseModel

from useq._pydantic_compat import PYDANTIC2, model_dump, model_fields

if TYPE_CHECKING:
    ReprArgs = Sequence[Tuple[Optional[str], Any]]
    IncEx = set[int] | set[str] | dict[int, Any] | dict[str, Any] | None

__all__ = ["UseqModel", "FrozenModel"]

_T = TypeVar("_T", bound="FrozenModel")
_Y = TypeVar("_Y", bound="UseqModel")


class FrozenModel(BaseModel):
    if PYDANTIC2:
        model_config = {
            "populate_by_name": True,
            "extra": "ignore",
            "frozen": True,
        }

    else:

        class Config:
            allow_population_by_field_name = True
            extra = "ignore"
            frozen = True
            json_encoders: ClassVar[dict] = {MappingProxyType: dict}

    def replace(self: _T, **kwargs: Any) -> _T:
        """Return a new instance replacing specified kwargs with new values.

        This model is immutable, so this method is useful for creating a new
        sequence with only a few fields changed.  The uid of the new sequence will
        be different from the original.

        The difference between this and `self.copy(update={...})` is that this method
        will perform validation and casting on the new values, whereas `copy` assumes
        that all objects are valid and will not perform any validation or casting.
        """
        state = model_dump(self, exclude={"uid"})
        return type(self)(**{**state, **kwargs})

    if PYDANTIC2:
        # retain pydantic1's json method
        def json(
            self,
            *,
            indent: int | None = None,  # type: ignore
            include: IncEx = None,
            exclude: IncEx = None,  # type: ignore
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,  # type: ignore
            round_trip: bool = False,
            warnings: bool = True,
        ) -> str:
            return super().model_dump_json(
                indent=indent,
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                round_trip=round_trip,
                warnings=warnings,
            )

        # we let this one be deprecated
        # def dict()

    elif not TYPE_CHECKING:
        # Backport pydantic2 methods so that useq-0.1.0 can be used with pydantic1

        def model_dump_json(self, **kwargs: Any) -> str:
            """Backport of pydantic2's model_dump_json method."""
            return self.json(**kwargs)

        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            """Backport of pydantic2's model_dump_json method."""
            return self.dict(**kwargs)


class UseqModel(FrozenModel):
    def __repr_args__(self) -> ReprArgs:
        """Only show fields that are not None or equal to their default value."""
        return [
            (k, val)
            for k, val in super().__repr_args__()
            if k in model_fields(self)
            and val
            != (
                factory()
                if (factory := model_fields(self)[k].default_factory) is not None
                else model_fields(self)[k].default
            )
        ]

    @classmethod
    def from_file(cls: Type[_Y], path: Union[str, Path]) -> _Y:
        """Return an instance of this class from a file.  Supports JSON and YAML."""
        path = Path(path)
        if path.suffix in {".yaml", ".yml"}:
            import yaml

            obj = yaml.safe_load(path.read_bytes())
        elif path.suffix == ".json":
            import json

            obj = json.loads(path.read_bytes())
        else:  # pragma: no cover
            raise ValueError(f"Unknown file type: {path.suffix}")

        return cls.model_validate(obj) if PYDANTIC2 else cls.parse_obj(obj)

    @classmethod
    def parse_file(cls: Type[_Y], path: Union[str, Path], **kwargs: Any) -> _Y:
        warnings.warn(  # pragma: no cover
            "parse_file is deprecated. Use from_file instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.from_file(path)  # pragma: no cover

    def yaml(
        self,
        *,
        include: Optional[Union[set, dict]] = None,
        exclude: Optional[Union[set, dict]] = None,
        by_alias: bool = False,
        exclude_unset: bool = True,  # pydantic has False by default
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        stream: Optional[IO[str]] = None,
    ) -> Optional[str]:
        """Generate a YAML representation of the model.

        Returns
        -------
        yaml : str or None
            YAML output ... If `stream` is provided, returns `None`.
        """
        from datetime import timedelta
        from enum import Enum

        import yaml

        yaml.SafeDumper.add_multi_representer(
            timedelta, lambda dumper, data: dumper.represent_str(str(data))
        )
        yaml.SafeDumper.add_multi_representer(
            Enum, lambda dumper, data: dumper.represent_str(str(data.value))
        )
        yaml.SafeDumper.add_multi_representer(
            MappingProxyType, lambda dumper, data: dumper.represent_dict(data)
        )
        yaml.SafeDumper.add_multi_representer(
            np.floating, lambda dumper, d: dumper.represent_float(float(d))
        )

        data = model_dump(
            self,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return yaml.safe_dump(data, stream=stream)
