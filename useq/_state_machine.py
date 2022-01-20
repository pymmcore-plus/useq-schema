from typing import Any, List, Union

from pydantic import validator
from transitions.extensions import GraphMachine

from ._base_model import UseqModel


def _str2list(val: Union[str, List[str]]) -> List[str]:
    return [val] if isinstance(val, str) else val


class Transition(UseqModel):
    trigger: str
    source: str
    dest: str
    conditions: List[str] = []
    unless: List[str] = []
    _vconditions = validator("conditions", pre=True, allow_reuse=True)(_str2list)
    _vunless = validator("unless", pre=True, allow_reuse=True)(_str2list)


class State(UseqModel):
    name: str
    on_enter: List[str] = []
    on_exit: List[str] = []
    _venter = validator("on_enter", pre=True, allow_reuse=True)(_str2list)
    _vexit = validator("on_exit", pre=True, allow_reuse=True)(_str2list)


class StateMachine(UseqModel):
    states: List[State]
    transitions: List[Transition]

    @validator("states", pre=True)
    def _validate_states(cls, value: Any):
        value = [{"name": v} if isinstance(v, str) else v for v in value]
        return value

    def draw(self, stream: Any):
        t = type("T", (), {"trigger": lambda: None})()
        machine = GraphMachine(t, **self.dict())
        machine.get_graph().draw(stream, prog="dot", format="png")
