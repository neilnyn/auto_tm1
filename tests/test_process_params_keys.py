"""Regression tests for case-insensitive parameter/variable keys in TI processes.

Covers the key-case bug: MCP callers / LLM-generated JSON (inline or from
parameters.json / variable.json) may use "Name", "Type" instead of lowercase
"name", "type". ``_apply_parameters_and_variables`` and ``execute_process``
must tolerate this (no KeyError) and must NOT silently degrade a Numeric
type to String.

Pure unit tests — TM1Manager is constructed but never connected; execute_process
gets a fake service via monkeypatch.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tm1_mcp_server"))

import pytest
from TM1py.Objects import Process

from tm1_connector import TM1Manager, _lower_keys

# Methods under test do not touch TM1, so no connect() is needed.
_mgr = TM1Manager("Neil")


def _param_pairs(process):
    """[(name, type)] from a Process — tm1py stores params as {'Name','Type'} dicts."""
    return [(p["Name"], p["Type"]) for p in (process.parameters or [])]


def _var_pairs(process):
    return [(v["Name"], v["Type"]) for v in (process.variables or [])]


# ── _lower_keys helper ──────────────────────────────────────────────


def test_lower_keys_lowercases_capitalized():
    assert _lower_keys({"Name": "p1", "Type": "Numeric"}) == {"name": "p1", "type": "Numeric"}


def test_lower_keys_handles_all_caps():
    assert _lower_keys({"NAME": "p1", "TYPE": "String"}) == {"name": "p1", "type": "String"}


def test_lower_keys_preserves_lowercase():
    assert _lower_keys({"name": "p1"}) == {"name": "p1"}


# ── _apply_parameters_and_variables ─────────────────────────────────


def test_apply_capitalized_name_no_keyerror():
    """Original bug: 'Name' (capital) raised KeyError('name')."""
    p = Process(name="T")
    _mgr._apply_parameters_and_variables(p, [{"Name": "p1", "type": "Numeric"}], None)
    assert ("p1", "Numeric") in _param_pairs(p)


def test_apply_capitalized_type_not_silently_degraded():
    """'Type' (capital) must still apply Numeric, not fall back to String."""
    p = Process(name="T")
    _mgr._apply_parameters_and_variables(p, [{"name": "p1", "Type": "Numeric"}], None)
    pairs = _param_pairs(p)
    assert ("p1", "Numeric") in pairs
    assert ("p1", "String") not in pairs


def test_apply_all_caps_keys():
    p = Process(name="T")
    _mgr._apply_parameters_and_variables(p, [{"NAME": "p1", "TYPE": "String"}], None)
    assert ("p1", "String") in _param_pairs(p)


def test_apply_capitalized_variable_keys():
    p = Process(name="T")
    _mgr._apply_parameters_and_variables(p, None, [{"Name": "v1", "Type": "Numeric"}])
    assert ("v1", "Numeric") in _var_pairs(p)


def test_apply_standard_lowercase_unchanged():
    """Existing lowercase usage must keep working (backward compatibility)."""
    p = Process(name="T")
    _mgr._apply_parameters_and_variables(
        p,
        [{"name": "p1", "prompt": "P", "value": "V", "type": "Numeric"}],
        [{"name": "v1", "type": "String"}],
    )
    assert ("p1", "Numeric") in _param_pairs(p)
    assert ("v1", "String") in _var_pairs(p)


def test_apply_missing_name_still_raises():
    """name is mandatory; its absence must still surface, not be silently skipped."""
    p = Process(name="T")
    with pytest.raises(KeyError):
        _mgr._apply_parameters_and_variables(p, [{"type": "Numeric"}], None)


# ── execute_process ─────────────────────────────────────────────────


def test_execute_process_reads_capitalized_name(monkeypatch):
    """execute_process builds kwargs[param-name]; a capital 'Name' must not KeyError."""
    captured = {}

    class _ProcSvc:
        def execute_with_return(self, name, timeout=None, **kwargs):
            captured["name"] = name
            captured["kwargs"] = kwargs
            return True, "Completed", None

    class _Service:
        processes = _ProcSvc()

    monkeypatch.setattr(_mgr, "_tm1", _Service())
    result = _mgr.execute_process("MyProc", parameters=[{"Name": "p1", "Value": "42"}])
    assert captured["name"] == "MyProc"
    assert captured["kwargs"] == {"p1": "42"}
    assert result["success"] is True
