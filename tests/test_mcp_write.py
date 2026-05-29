"""MCP integration tests — write tools via FastMCP in-memory Client.

Covers: create_dimension, delete_dimension, add_elements, delete_elements,
update_hierarchy, create_element_attribute, write_element_attributes,
create_cube, delete_cube, write_cell, write_bulk, write_file, clear_cube,
create_view, delete_view, create_subset, update_subset, delete_subset,
create_process, update_process, compile_process, get_process,
delete_process, execute_process, verify_dimension, verify_cube.
"""

import csv
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tm1_mcp_server"))
from tm1_mcp_tool import mcp

INSTANCE = "Neil"
PREFIX = "Claude_Test_MCP"

# Shared test object names
DIM = f"{PREFIX}_Dim"
DIM2 = f"{PREFIX}_Dim2"
DIMS_CUBE = [f"{PREFIX}_D1", f"{PREFIX}_D2", f"{PREFIX}_D3"]
CUBE = f"{PREFIX}_Cube"
CUBE2 = f"{PREFIX}_Cube2"
PROC = f"{PREFIX}_Proc"
VIEW = f"{PREFIX}_View"
SUB = f"{PREFIX}_Sub"


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        yield client


@pytest.fixture(autouse=True)
def cleanup(tm1_manager):
    """Clean up all test objects before and after each test."""
    mgr = tm1_manager
    _cleanup_all(mgr)
    yield
    _cleanup_all(mgr)


def _cleanup_all(mgr):
    for name in [PROC]:
        try:
            mgr.delete_process(name)
        except Exception:
            pass
    for cube in [CUBE, CUBE2]:
        try:
            mgr.delete_cube(cube)
        except Exception:
            pass
    for dim in DIMS_CUBE + [DIM, DIM2]:
        try:
            mgr.delete_dimension(dim)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# Dimension write tools
# ═══════════════════════════════════════════════════════════════════════

async def test_create_and_delete_dimension(
    mcp_client: Client[FastMCPTransport],
):
    r = await mcp_client.call_tool("create_dimension", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "elements": [
            {"name": "Total", "type": "Consolidated"},
            {"name": "A", "type": "Numeric"},
            {"name": "B", "type": "Numeric"},
        ],
        "edges": [
            {"parent": "Total", "child": "A", "weight": 1.0},
            {"parent": "Total", "child": "B", "weight": 1.0},
        ],
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["element_count"] == 3

    # delete
    d = await mcp_client.call_tool("delete_dimension", {
        "instance": INSTANCE, "dimension_name": DIM,
    })
    assert d.data["result"]["success"] is True


async def test_add_elements(mcp_client: Client[FastMCPTransport], tm1_manager):
    tm1_manager.create_dimension(DIM, [{"name": "Original", "type": "Numeric"}])

    r = await mcp_client.call_tool("add_elements", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "elements": [
            {"name": "Added1", "type": "Numeric"},
            {"name": "Added2", "type": "String"},
        ],
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["added_count"] == 2

    info = await mcp_client.call_tool("get_dimension_info", {
        "instance": INSTANCE, "dimension_name": DIM,
    })
    assert info.data["result"]["element_counts"]["total"] == 3


async def test_delete_elements(mcp_client: Client[FastMCPTransport], tm1_manager):
    tm1_manager.create_dimension(DIM, [
        {"name": "Keep", "type": "Numeric"},
        {"name": "Remove1", "type": "Numeric"},
        {"name": "Remove2", "type": "String"},
    ])

    r = await mcp_client.call_tool("delete_elements", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "element_names": ["Remove1", "Remove2"],
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["deleted_count"] == 2

    info = await mcp_client.call_tool("get_dimension_info", {
        "instance": INSTANCE, "dimension_name": DIM,
    })
    assert info.data["result"]["element_counts"]["total"] == 1


async def test_update_hierarchy(mcp_client: Client[FastMCPTransport], tm1_manager):
    tm1_manager.create_dimension(DIM, [
        {"name": "Top", "type": "Consolidated"},
        {"name": "Child1", "type": "Numeric"},
        {"name": "Child2", "type": "Numeric"},
    ])

    # add edges
    r = await mcp_client.call_tool("update_hierarchy", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "add_edges": [
            {"parent": "Top", "child": "Child1", "weight": 1.0},
            {"parent": "Top", "child": "Child2", "weight": 2.0},
        ],
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["edges_added"] == 2

    parents = await mcp_client.call_tool("get_parents", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "elements": ["Child1", "Child2"],
    })
    assert parents.data["result"]["parents"]["Child1"] == ["Top"]

    # remove edge
    r2 = await mcp_client.call_tool("update_hierarchy", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "remove_edges": [{"parent": "Top", "child": "Child2"}],
    })
    assert r2.data["result"]["edges_removed"] == 1


async def test_create_element_attribute(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    tm1_manager.create_dimension(DIM, [{"name": "X", "type": "Numeric"}])

    r = await mcp_client.call_tool("create_element_attribute", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "attribute_name": "TestAttr",
        "attribute_type": "String",
    })
    assert r.data["result"]["success"] is True

    info = await mcp_client.call_tool("get_dimension_info", {
        "instance": INSTANCE, "dimension_name": DIM,
    })
    assert "TestAttr" in info.data["result"]["attribute_names"]


async def test_write_element_attributes(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    tm1_manager.create_dimension(DIM, [
        {"name": "Q1", "type": "Numeric"},
        {"name": "Q2", "type": "Numeric"},
    ])
    tm1_manager.create_element_attribute(DIM, "Alias", "Alias")

    r = await mcp_client.call_tool("write_element_attributes", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "attribute_values": [
            {"element": "Q1", "attribute": "Alias", "value": "Quarter 1"},
            {"element": "Q2", "attribute": "Alias", "value": "Quarter 2"},
        ],
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["values_updated"] == 2

    attrs = await mcp_client.call_tool("get_element_attributes", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "elements": ["Q1", "Q2"],
        "attribute_names": ["Alias"],
    })
    assert attrs.data["result"]["attributes"]["Q1"]["Alias"] == "Quarter 1"
    assert attrs.data["result"]["attributes"]["Q2"]["Alias"] == "Quarter 2"


# ═══════════════════════════════════════════════════════════════════════
# Cube write tools
# ═══════════════════════════════════════════════════════════════════════

def _create_test_dims_and_cube(mgr):
    for dim in DIMS_CUBE:
        mgr.create_dimension(dim, [
            {"name": "E1", "type": "Numeric"},
            {"name": "E2", "type": "Numeric"},
        ])
    mgr.create_cube(CUBE, DIMS_CUBE)


async def test_create_and_delete_cube(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    for dim in DIMS_CUBE:
        tm1_manager.create_dimension(dim, [{"name": "E1", "type": "Numeric"}])

    r = await mcp_client.call_tool("create_cube", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "dimensions": DIMS_CUBE,
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["dimensions"] == DIMS_CUBE

    d = await mcp_client.call_tool("delete_cube", {
        "instance": INSTANCE, "cube_name": CUBE,
    })
    assert d.data["result"]["success"] is True


async def test_write_and_read_cell(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    _create_test_dims_and_cube(mgr=tm1_manager)

    await mcp_client.call_tool("write_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E1", "E1", "E1"],
        "value": 42.5,
    })

    r = await mcp_client.call_tool("get_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E1", "E1", "E1"],
    })
    assert r.data["result"] == 42.5


async def test_write_bulk(mcp_client: Client[FastMCPTransport], tm1_manager):
    _create_test_dims_and_cube(mgr=tm1_manager)

    r = await mcp_client.call_tool("write_bulk", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "cellset": {
            "('E1','E1','E1')": 10,
            "('E2','E1','E1')": 20,
            "('E1','E2','E1')": 30,
        },
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["cells_written"] == 3

    # verify one cell
    c = await mcp_client.call_tool("get_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E2", "E1", "E1"],
    })
    assert c.data["result"] == 20


async def test_write_file(mcp_client: Client[FastMCPTransport], tm1_manager):
    _create_test_dims_and_cube(mgr=tm1_manager)

    csv_path = os.path.join(tempfile.gettempdir(), "claude_test_mcp_write.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(DIMS_CUBE + ["Value"])  # header row
        writer.writerow(["E1", "E1", "E1", 99.5])

    r = await mcp_client.call_tool("write_file", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "file_path": csv_path,
    })
    assert r.data["result"]["success"] is True
    assert r.data["result"]["rows_written"] >= 1

    c = await mcp_client.call_tool("get_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E1", "E1", "E1"],
    })
    assert c.data["result"] == 99.5

    os.remove(csv_path)


async def test_clear_cube(mcp_client: Client[FastMCPTransport], tm1_manager):
    _create_test_dims_and_cube(mgr=tm1_manager)
    tm1_manager.write_cell(CUBE, ["E1", "E1", "E1"], 100)

    # Verify data exists
    c = await mcp_client.call_tool("get_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E1", "E1", "E1"],
    })
    assert c.data["result"] == 100

    r = await mcp_client.call_tool("clear_cube", {
        "instance": INSTANCE,
        "cube_name": CUBE,
    })
    assert r.data["result"]["success"] is True

    # Verify cell is now empty (TM1 returns None for cleared cells)
    c2 = await mcp_client.call_tool("get_cell", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "elements": ["E1", "E1", "E1"],
    })
    assert c2.data["result"] in (0, None)


# ═══════════════════════════════════════════════════════════════════════
# View write tools
# ═══════════════════════════════════════════════════════════════════════

async def test_create_and_delete_view(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    _create_test_dims_and_cube(mgr=tm1_manager)

    mdx = (
        f"SELECT "
        f"{{[{{{DIMS_CUBE[0]}}}].[E1]}} ON 0, "
        f"{{[{{{DIMS_CUBE[1]}}}].[E1]}} ON 1 "
        f"FROM [{CUBE}]"
    )
    r = await mcp_client.call_tool("create_view", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "view_name": VIEW,
        "mdx": mdx,
    })
    assert r.data["result"]["success"] is True

    # verify it appears in list_views
    views = await mcp_client.call_tool("list_views", {
        "instance": INSTANCE, "cube_name": CUBE,
    })
    assert VIEW in views.data["result"]["public"]

    # delete
    d = await mcp_client.call_tool("delete_view", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "view_name": VIEW,
    })
    assert d.data["result"]["success"] is True


# ═══════════════════════════════════════════════════════════════════════
# Subset write tools
# ═══════════════════════════════════════════════════════════════════════

async def test_create_update_delete_subset(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    tm1_manager.create_dimension(DIM, [
        {"name": "A", "type": "Numeric"},
        {"name": "B", "type": "Numeric"},
        {"name": "C", "type": "Numeric"},
    ])

    # create static subset
    r = await mcp_client.call_tool("create_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
        "elements": ["A", "C"],
    })
    assert r.data["result"]["success"] is True

    sub = await mcp_client.call_tool("get_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
    })
    assert sub.data["result"]["subset_type"] == "static"
    assert sub.data["result"]["element_count"] == 2

    # update to different elements
    u = await mcp_client.call_tool("update_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
        "elements": ["B"],
    })
    assert u.data["result"]["success"] is True

    sub2 = await mcp_client.call_tool("get_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
    })
    assert sub2.data["result"]["element_count"] == 1

    # delete
    d = await mcp_client.call_tool("delete_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
    })
    assert d.data["result"]["success"] is True


async def test_create_dynamic_subset(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    tm1_manager.create_dimension(DIM, [
        {"name": "A", "type": "Numeric"},
        {"name": "B", "type": "Numeric"},
    ])

    r = await mcp_client.call_tool("create_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
        "expression": f"{{TM1FilterByLevel({{TM1SubsetAll([{{{DIM}}}])}}, 0)}}",
    })
    assert r.data["result"]["success"] is True

    sub = await mcp_client.call_tool("get_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
    })
    assert sub.data["result"]["subset_type"] == "dynamic"

    # cleanup
    await mcp_client.call_tool("delete_subset", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "subset_name": SUB,
    })


# ═══════════════════════════════════════════════════════════════════════
# Process write tools
# ═══════════════════════════════════════════════════════════════════════

async def test_create_compile_get_delete_process(
    mcp_client: Client[FastMCPTransport],
):
    r = await mcp_client.call_tool("create_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "prolog": "sMsg = 'Hello from MCP test';",
        "epilog": "LogOutput('INFO', sMsg);",
        "parameters": [
            {"name": "pMsg", "prompt": "Message", "value": "test", "type": "String"},
        ],
    })
    assert r.data["result"]["success"] is True

    # compile
    comp = await mcp_client.call_tool("compile_process", {
        "instance": INSTANCE, "process_name": PROC,
    })
    assert comp.data["result"]["has_errors"] is False

    # get_process
    proc = await mcp_client.call_tool("get_process", {
        "instance": INSTANCE, "process_name": PROC, "include_code": True,
    })
    proc_data = proc.data["result"]
    assert proc_data["name"] == PROC
    assert len(proc_data["parameters"]) == 1
    assert proc_data["parameters"][0]["Name"] == "pMsg"
    assert "sMsg" in proc_data["prolog_procedure"]

    # delete
    d = await mcp_client.call_tool("delete_process", {
        "instance": INSTANCE, "process_name": PROC,
    })
    assert d.data["result"]["success"] is True


async def test_update_process(mcp_client: Client[FastMCPTransport]):
    await mcp_client.call_tool("create_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "prolog": "nOriginal = 1;",
    })

    r = await mcp_client.call_tool("update_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "prolog": "nUpdated = 2;",
    })
    assert r.data["result"]["success"] is True

    proc = await mcp_client.call_tool("get_process", {
        "instance": INSTANCE, "process_name": PROC,
    })
    assert "nUpdated" in proc.data["result"]["prolog_procedure"]
    assert "nOriginal" not in proc.data["result"]["prolog_procedure"]


async def test_execute_process_success(mcp_client: Client[FastMCPTransport]):
    await mcp_client.call_tool("create_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "prolog": "nTest = 1 + 1;",
    })

    r = await mcp_client.call_tool("execute_process", {
        "instance": INSTANCE,
        "process_name": PROC,
    })
    assert r.data["result"]["success"] is True


async def test_execute_process_with_params(mcp_client: Client[FastMCPTransport]):
    await mcp_client.call_tool("create_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "prolog": "sGreeting = 'Hello ' | pName | '!';",
        "parameters": [
            {"name": "pName", "prompt": "Name", "value": "World", "type": "String"},
        ],
    })

    r = await mcp_client.call_tool("execute_process", {
        "instance": INSTANCE,
        "process_name": PROC,
        "parameters": [
            {"name": "pName", "value": "MCP Test"},
        ],
    })
    assert r.data["result"]["success"] is True


# ═══════════════════════════════════════════════════════════════════════
# Verification tools
# ═══════════════════════════════════════════════════════════════════════

async def test_verify_dimension_via_mcp(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    tm1_manager.create_dimension(DIM, [
        {"name": "A", "type": "Numeric"},
        {"name": "B", "type": "String"},
    ])

    r = await mcp_client.call_tool("verify_dimension", {
        "instance": INSTANCE,
        "dimension_name": DIM,
        "expected_elements": {"Numeric": 1, "String": 1},
    })
    assert r.data["result"]["match"] is True


async def test_verify_cube_via_mcp(
    mcp_client: Client[FastMCPTransport], tm1_manager,
):
    for dim in DIMS_CUBE:
        tm1_manager.create_dimension(dim, [{"name": "E1", "type": "Numeric"}])
    tm1_manager.create_cube(CUBE, DIMS_CUBE)

    r = await mcp_client.call_tool("verify_cube", {
        "instance": INSTANCE,
        "cube_name": CUBE,
        "expected_dimensions": DIMS_CUBE,
    })
    assert r.data["result"]["match"] is True
