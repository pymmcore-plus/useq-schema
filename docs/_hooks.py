"""Functions defined in this module are called by MkDocs at various points.

during the build process.

See: https://www.mkdocs.org/dev-guide/plugins/#events
for the various events that can be hooked into.

For example, we use the `on_pre_build` event to generate the markdown table for the
CMMCorePlus API page.
"""
import collections.abc
import re
from importlib import import_module
from typing import Any, TypeVar, Union

from pydantic import BaseModel
from typing_extensions import ParamSpec

TABLE_RE = re.compile("{{ pydantic_table \\|\s([^\s]*)\s}}")


def on_page_markdown(md: str, page, config, files) -> str:
    """Called after the page's markdown is loaded from file.

    can be used to alter the Markdown source text.
    """
    for name in TABLE_RE.findall(md):
        table = f"## `{name}`\n{_pydantic_table(name)}"
        md = md.replace(f"{{{{ pydantic_table | {name} }}}}", table)
    return md


def _pydantic_table(name: str) -> str:
    mod, attr = name.rsplit(".", 1)
    cls = getattr(import_module(mod), attr)
    assert issubclass(cls, BaseModel)
    rows = ["| Field | Type | Description |", "| ----  | ---- | ----------- |"]
    for f in cls.__fields__.values():
        type_ = _build_type_link(f.outer_type_)
        row = f"| {f.name} | {type_} | {f.field_info.description} |"
        rows.append(row)
    return "\n".join(rows)


def _type_link(typ: Any) -> str:
    if typ is Ellipsis:
        return "[`...`][types.EllipsisType]"
    mod = f"{typ.__module__}." if typ.__module__ != "builtins" else ""
    type_fullpath = f"{mod}{typ.__name__}"
    return f"[`{typ.__name__}`][{type_fullpath}]"


def _build_type_link(typ: Any) -> str:
    origin = getattr(typ, "__origin__", None)
    if origin is None:
        return _type_link(typ)

    args = getattr(typ, "__args__", ())
    if origin is collections.abc.Callable and any(
        isinstance(a, (TypeVar, ParamSpec)) for a in args
    ):
        return _type_link(origin)
    types = [_build_type_link(a) for a in args if a is not type(None)]  # noqa
    if origin is Union:
        return " or ".join(types)
    type_ = ", ".join(types)
    return f"{_type_link(origin)}[{type_}]"
