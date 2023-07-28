from __future__ import annotations

import warnings
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np
from pydantic import BaseModel, root_validator
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from pydantic.utils import ROOT_KEY

from useq._utils import ReadOnlyDict

if TYPE_CHECKING:
    from pydantic.types import StrBytes

    ReprArgs = Sequence[Tuple[Optional[str], Any]]


__all__ = ["UseqModel", "FrozenModel"]

_T = TypeVar("_T", bound="FrozenModel")
_Y = TypeVar("_Y", bound="UseqModel")


class FrozenModel(BaseModel):
    class Config:
        allow_population_by_field_name = True
        extra = "allow"
        frozen = True
        json_encoders: ClassVar[dict] = {"ReadOnlyDict": dict}

    @root_validator(pre=False, skip_on_failure=True)
    def _validate_kwargs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate kwargs for MDASequence."""
        extra_kwargs = set(values) - set(cls.__fields__)
        if extra_kwargs:
            name = getattr(cls, "__name__", "")
            warnings.warn(
                f"{name} got unknown keyword arguments: {extra_kwargs}", stacklevel=2
            )
            for k in extra_kwargs:
                values.pop(k)
        return values

    def replace(self: _T, **kwargs: Any) -> _T:
        """Return a new instance replacing specified kwargs with new values.

        This model is immutable, so this method is useful for creating a new
        sequence with only a few fields changed.  The uid of the new sequence will
        be different from the original.

        The difference between this and `self.copy(update={...})` is that this method
        will perform validation and casting on the new values, whereas `copy` assumes
        that all objects are valid and will not perform any validation or casting.
        """
        state = self.dict(exclude={"uid"})
        return type(self)(**{**state, **kwargs})


class UseqModel(FrozenModel):
    def __repr_args__(self) -> ReprArgs:
        return [
            (k, val)
            for k, val in super().__repr_args__()
            if k in self.__fields__
            and val
            != (
                self.__fields__[k].default_factory()  # type: ignore
                if self.__fields__[k].default_factory is not None
                else self.__fields__[k].default
            )
        ]

    def __repr__(self) -> str:
        """Repr, that only shows values that are changed form the defaults."""
        from textwrap import indent

        lines = []
        for k, current in sorted(self.__repr_args__()):
            if not k:
                continue
            f = self.__fields__[k]
            default = (
                self.__fields__[k].default_factory()  # type: ignore
                if self.__fields__[k].default_factory is not None
                else self.__fields__[k].default
            )
            if current != default:
                lines.append(f"{f.name}={current!r},")
        if len(lines) == 1:
            body = lines[-1].rstrip(",")
        elif lines:
            body = "\n" + indent("\n".join(lines), "   ") + "\n"
        else:
            body = ""
        return f"{self.__class__.__qualname__}({body})"

    @classmethod
    def parse_raw(
        cls: Type[_Y],
        b: StrBytes,
        *,
        content_type: Optional[str] = None,
        encoding: str = "utf8",
        proto: Optional[str] = None,
        allow_pickle: bool = False,
    ) -> _Y:
        if content_type is None:
            assume_yaml = False
        else:
            assume_yaml = ("yaml" in content_type) or ("yml" in content_type)

        if proto == "yaml" or assume_yaml:
            import yaml

            try:
                obj = yaml.safe_load(b)
            except Exception as e:
                raise ValidationError([ErrorWrapper(e, loc=ROOT_KEY)], cls) from e
            return cls.parse_obj(obj)
        return super().parse_raw(
            b,
            content_type=content_type,  # type: ignore
            encoding=encoding,
            proto=proto,  # type: ignore
            allow_pickle=allow_pickle,
        )

    @classmethod
    def parse_file(
        cls: Type[_Y],
        path: Union[str, Path],
        *,
        content_type: Optional[str] = None,
        encoding: str = "utf8",
        proto: Optional[str] = None,
        allow_pickle: bool = False,
    ) -> _Y:
        if encoding is None:
            assume_yaml = False
        elif content_type:
            assume_yaml = ("yaml" in content_type) or ("yml" in content_type)
        else:
            assume_yaml = str(path).endswith((".yml", ".yaml"))

        if proto == "yaml" or assume_yaml:
            return cls.parse_raw(
                Path(path).read_bytes(),
                content_type=content_type or "application/yaml",
                encoding=encoding,
                proto="yaml",
                allow_pickle=allow_pickle,
            )

        return super().parse_file(
            path,
            content_type=content_type,  # type: ignore
            encoding=encoding,
            proto=proto,  # type: ignore
            allow_pickle=allow_pickle,
        )

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
            ReadOnlyDict, lambda dumper, data: dumper.represent_dict(data)
        )
        yaml.SafeDumper.add_multi_representer(
            np.floating, lambda dumper, data: dumper.represent_float(float(data))
        )

        data = self.dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return yaml.safe_dump(data, stream=stream)
