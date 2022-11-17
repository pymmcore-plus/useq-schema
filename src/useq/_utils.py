from typing import Iterable, Iterator, Mapping, Tuple, TypeVar, Union

KT = TypeVar("KT")
VT = TypeVar("VT")


class ReadOnlyDict(Mapping[KT, VT]):
    def __init__(
        self, data: Union[Mapping[KT, VT], Iterable[Tuple[KT, VT]]] = ()
    ) -> None:
        self._data = dict(data)

    def __getitem__(self, key: KT) -> VT:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[KT]:
        return iter(self._data)

    def __repr__(self) -> str:
        return repr(self._data)
