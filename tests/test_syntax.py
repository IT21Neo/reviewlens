"""Every .py file must compile on the Python that runs the tests (catches syntax that only
newer Pythons accept, e.g. reused quotes inside f-strings before 3.12)."""
import py_compile
from pathlib import Path

import pytest

FILES = sorted(p for d in ("app", "scripts") for p in Path(d).rglob("*.py"))


@pytest.mark.parametrize("path", FILES, ids=str)
def test_compiles(path):
    py_compile.compile(str(path), doraise=True)
