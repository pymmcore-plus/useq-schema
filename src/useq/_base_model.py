from pathlib import Path
from types import MappingProxyType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
)

import numpy as np
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from typing_extensions import Self

    ReprArgs = Iterable[tuple[str | None, Any]]

__all__ = ["UseqModel", "FrozenModel"]

_T = TypeVar("_T", bound="FrozenModel")
_Y = TypeVar("_Y", bound="UseqModel")


def _non_default_repr_args(obj: BaseModel, fields: "ReprArgs") -> "ReprArgs":
    """Set fields on a model instance."""
    return [
        (k, val)
        for k, val in fields
        if k in obj.model_fields
        and val
        != (
            factory()
            if (factory := obj.model_fields[k].default_factory) is not None
            else obj.model_fields[k].default
        )
    ]


# TODO: consider removing this and using model_copy directly
class _ReplaceableModel(BaseModel):
    def replace(self, **kwargs: Any) -> "Self":
        """Return a new instance replacing specified kwargs with new values.

        This model is immutable, so this method is useful for creating a new
        sequence with only a few fields changed.  The uid of the new sequence will
        be different from the original.

        The difference between this and `self.model_copy(update={...})` is that this
        method will perform validation and casting on the new values, whereas `copy`
        assumes that all objects are valid and will not perform any validation or
        casting.
        """
        # only get values for top level fields
        d = {k: getattr(self, k) for k in self.model_fields if k != "uid"}
        return type(self).model_validate({**d, **kwargs})

    def __repr_args__(self) -> "ReprArgs":
        """Only show fields that are not None or equal to their default value."""
        return _non_default_repr_args(self, super().__repr_args__())


class FrozenModel(_ReplaceableModel):
    model_config: ClassVar["ConfigDict"] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        frozen=True,
        json_encoders={MappingProxyType: dict},
    )


class MutableModel(_ReplaceableModel):
    model_config: ClassVar["ConfigDict"] = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        validate_default=True,
        extra="ignore",
    )


class UseqModel(FrozenModel):
    @classmethod
    def from_file(cls: Type[_Y], path: Union[str, Path]) -> _Y:
        """Return an instance of this class from a file.  Supports JSON and YAML."""
        path = Path(path)
        if path.suffix in {".yaml", ".yml"}:
            import yaml

            obj = yaml.safe_load(path.read_bytes())
        elif path.suffix == ".json":
            return cls.model_validate_json(path.read_bytes())
        else:  # pragma: no cover
            raise ValueError(f"Unknown file type: {path.suffix}")

        return cls.model_validate(obj)

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

        data = self.model_dump(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return yaml.safe_dump(data, stream=stream)
