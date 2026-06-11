"""Regression tests for hooks/cc_workon.py — cc-workon path parsing.

Pure unit tests: PROJECT_ROOT is monkeypatched to a tmp dir and the
sessions.json store is replaced with an in-memory dict, so no real session
file or TM1 connection is touched.

Covers the space-in-path bug fix: quoted paths ("..."/'...') must preserve
inner spaces, while unquoted spaces are rejected rather than silently
truncating to the first token.
"""

import contextlib
import io
import os
import sys
from pathlib import Path

import pytest

# Make the hooks/ package importable (conftest only adds tm1_mcp_server).
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import cc_workon  # noqa: E402


def _invoke(command, cwd):
    """Run handle_cc_workon, capturing the hook exit code + messages.

    acknowledge() exits 0 and prints JSON to stdout; block() exits 2 and
    prints the message to stderr.
    """
    err = io.StringIO()
    out = io.StringIO()
    code = None
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        try:
            cc_workon.handle_cc_workon(command, cwd, "s1")
            code = 0
        except SystemExit as exc:
            code = int(exc.code) if exc.code is not None else 0
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def cc_env(tmp_path, monkeypatch):
    """Patch cc_workon to use tmp_path as PROJECT_ROOT + in-memory sessions."""
    store = {}
    cwd = str(tmp_path)
    monkeypatch.setattr(cc_workon, "PROJECT_ROOT", cwd)
    monkeypatch.setattr(cc_workon, "load_sessions", lambda: dict(store))
    monkeypatch.setattr(
        cc_workon, "save_sessions", lambda d: (store.clear(), store.update(d))
    )
    monkeypatch.setattr(cc_workon, "cleanup_stale_sessions", lambda d: False)
    return cwd, store


def test_standard_underscore_path_registers(cc_env):
    cwd, store = cc_env
    os.makedirs(os.path.join(cwd, "models", "Sales_Planning"))
    code, _out, _err = _invoke("cc-workon models/Sales_Planning", cwd)
    assert code == 0
    assert store["s1"]["project"] == "models/Sales_Planning"


def test_double_quoted_space_path_registers(cc_env):
    """Core fix: a double-quoted path with spaces registers in full."""
    cwd, store = cc_env
    os.makedirs(os.path.join(cwd, "models", "Sales Planning"))
    code, _out, _err = _invoke('cc-workon "models/Sales Planning"', cwd)
    assert code == 0
    assert store["s1"]["project"] == "models/Sales Planning"


def test_single_quoted_space_path_registers(cc_env):
    """Core fix: a single-quoted path with spaces registers in full."""
    cwd, store = cc_env
    os.makedirs(os.path.join(cwd, "models", "Sales Planning"))
    code, _out, _err = _invoke("cc-workon 'models/Sales Planning'", cwd)
    assert code == 0
    assert store["s1"]["project"] == "models/Sales Planning"


def test_unquoted_space_path_rejected(cc_env):
    """Regression guard: unquoted spaces must NOT silently truncate + register."""
    cwd, store = cc_env
    os.makedirs(os.path.join(cwd, "models", "Sales Planning"))
    code, _out, err = _invoke("cc-workon models/Sales Planning", cwd)
    assert code == 2
    assert "s1" not in store
    assert "does not exist" in err.lower()


def test_empty_quoted_path_rejected(cc_env):
    """Empty quotes must be rejected, never register the cwd as the project."""
    cwd, store = cc_env
    code, _out, _err = _invoke('cc-workon ""', cwd)
    assert code == 2
    assert "s1" not in store


def test_path_outside_root_rejected(cc_env):
    """Paths outside the project root are blocked (traversal guard)."""
    cwd, store = cc_env
    outside = os.path.join(os.path.dirname(cwd), "auto_tm1_outside")
    os.makedirs(outside, exist_ok=True)
    code, _out, _err = _invoke(f'cc-workon "{outside}"', cwd)
    assert code == 2
    assert "s1" not in store


def test_nonexistent_directory_rejected(cc_env):
    """A non-existent path is blocked before any registration."""
    cwd, store = cc_env
    code, _out, _err = _invoke("cc-workon models/Does_Not_Exist", cwd)
    assert code == 2
    assert "s1" not in store
