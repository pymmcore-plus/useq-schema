from typing import Any, List

from ._base_model import UseqModel


class Transition(UseqModel):
    trigger: str
    source: str
    dest: str
    conditions: List[str] = []
    unless: List[str] = []


class State(UseqModel):
    name: str
    on_enter: List[str] = []
    on_exit: List[str] = []


class StateMachine(UseqModel):
    states: List[State]
    transitions: List[Transition]

    def draw(self, stream: Any):
        from transitions.extensions import GraphMachine

        t = type("T", (), {"trigger": lambda: None})()
        machine = GraphMachine(t, **self.dict())
        machine.get_graph().draw(stream, prog="dot", format="png")
