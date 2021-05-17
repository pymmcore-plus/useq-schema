from __future__ import annotations

from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Optional, Sequence, Tuple, Type, Union

from pydantic import BaseModel
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from pydantic.types import StrBytes
from pydantic.utils import ROOT_KEY

if TYPE_CHECKING:
    ReprArgs = Sequence[Tuple[Optional[str], Any]]


__all__ = ["UseqModel"]


class UseqModel(BaseModel):
    class Config:
        allow_population_by_field_name = True
        extra = "forbid"
        validate_assignment = True

    def __repr_args__(self) -> ReprArgs:
        return [
            (k, val)
            for k, val in super().__repr_args__()
            if k in self.__fields__
            and val
            != (
                self.__fields__[k].default_factory()  # type: ignore
                if self.__fields__[k].default_factory
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
                if self.__fields__[k].default_factory
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
        cls: Type[UseqModel],
        b: StrBytes,
        *,
        content_type: Optional[str] = None,
        encoding: str = "utf8",
        proto: Optional[str] = None,
        allow_pickle: bool = False,
    ) -> UseqModel:
        if content_type is None:
            assume_yaml = False
        else:
            assume_yaml = ("yaml" in content_type) or ("yml" in content_type)

        if proto == "yaml" or assume_yaml:
            import yaml

            try:
                obj = yaml.safe_load(b)
            except Exception as e:
                raise ValidationError([ErrorWrapper(e, loc=ROOT_KEY)], cls)
            return cls.parse_obj(obj)
        return super().parse_raw(
            b,
            content_type=content_type,
            encoding=encoding,
            proto=proto,  # type: ignore
            allow_pickle=allow_pickle,
        )

    @classmethod
    def parse_file(
        cls: Type[UseqModel],
        path: Union[str, Path],
        *,
        content_type: Optional[str] = None,
        encoding: str = "utf8",
        proto: Optional[str] = None,
        allow_pickle: bool = False,
    ) -> UseqModel:
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
            content_type=content_type,
            encoding=encoding,
            proto=proto,  # type: ignore
            allow_pickle=allow_pickle,
        )

    def yaml(
        self,
        *,
        include: Union[set, dict] = None,
        exclude: Union[set, dict] = None,
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

        import yaml

        yaml.SafeDumper.add_multi_representer(
            timedelta, lambda dumper, data: dumper.represent_str(str(data))
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
