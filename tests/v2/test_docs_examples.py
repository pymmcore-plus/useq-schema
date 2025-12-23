"""Test that all code examples in the migration guide are valid and runnable.

This test extracts Python code blocks from the v2 migration guide and runs them
to ensure the documentation examples are accurate and functional.

Code blocks can be skipped by using a special comment marker at the start:
- # notest: Skips the entire block
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

DOCS_PATH = Path(__file__).parent.parent.parent / "docs" / "v2-migration.md"
CODE_PATTERN = re.compile(r"```python\n(.*?)```", re.DOTALL)


def test_code_block(capsys: pytest.CaptureFixture) -> None:
    """Test that a code block from the documentation runs without error."""
    exec_globals: dict[str, Any] = {}
    docs_src = DOCS_PATH.read_text()
    for code_block in CODE_PATTERN.finditer(docs_src):
        code = code_block.group(1)

        # Skip empty blocks
        if not code.strip():
            continue

        try:
            exec(code, exec_globals)  # noqa: S102
        except Exception as e:
            pytest.fail(f"Code block raised an exception:\n\n{code}\n\nException: {e}")
