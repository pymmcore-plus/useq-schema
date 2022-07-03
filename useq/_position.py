from __future__ import annotations

from typing import Any, Callable, Generator, Optional

import numpy as np
from pydantic import BaseModel, Field

from ._z import AnyZPlan, NoZ


class Position(BaseModel):
    # if None, implies 'do not move this axis'
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    name: Optional[str] = None
    z_plan: AnyZPlan = Field(default_factory=NoZ)

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[..., Any], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> Position:
        if isinstance(value, Position):
            return value
        if isinstance(value, dict):
            return Position(**value)
        if isinstance(value, (np.ndarray, tuple)):
            x, *value = value
            y, *value = value or (None,)
            if value:
                if len(value) == 1:
                    if isinstance(value[0], str):
                        name = value[0]
                        z = None
                    else:
                        z = value[0]
                        name = None
                else:
                    z = value[0]
                    name = value[1]
            else:
                z = None
                name = None

            return Position(name=name, x=x, y=y, z=z)
        raise TypeError(f"Cannot coerce {value!r} to Position")

def f(**kwargs):
    for key, value in kwargs.items():
        print(key, value)