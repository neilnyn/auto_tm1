"""Shared test fixtures for TM1 MCP tool tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tm1_mcp_server"))
from tm1_connector import TM1Manager


@pytest.fixture(scope="session")
def tm1_manager():
    """Session-scoped TM1Manager connected to the Neil instance."""
    mgr = TM1Manager("Neil").connect()
    yield mgr
    mgr.disconnect()
