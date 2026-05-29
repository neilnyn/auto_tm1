"""MCP integration tests — read-only tools via FastMCP in-memory Client.

Covers: list_instances, list_dimensions, get_dimension_info,
get_leaf_elements, expand_element, get_parents, get_element_attributes,
list_cubes, get_cube, find_cubes_by_dimension, get_cube_rules,
list_views, get_view_structure, list_subsets,
get_cell, execute_mdx, execute_view_query,
list_processes, get_process_template, get_process_error_log,
search_processes.
"""

import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tm1_mcp_server"))
from tm1_mcp_tool import mcp

INSTANCE = "Neil"


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        yield client


# ── list_instances ───────────────────────────────────────────────────────

async def test_list_instances(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool("list_instances", {})
    assert isinstance(result.data, list)
    assert "Neil" in result.data


# ── list_dimensions ─────────────────────────────────────────────────────

async def test_list_dimensions(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)
    assert len(data["result"]) > 0


async def test_list_dimensions_with_filter(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "list_dimensions",
        {"instance": INSTANCE, "filter": "period"},
    )
    data = result.data
    assert "result" in data
    for dim in data["result"]:
        assert "period" in dim.lower()


# ── get_dimension_info ──────────────────────────────────────────────────

async def test_get_dimension_info(mcp_client: Client[FastMCPTransport]):
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    first_dim = dims.data["result"][0]

    result = await mcp_client.call_tool(
        "get_dimension_info",
        {"instance": INSTANCE, "dimension_name": first_dim},
    )
    data = result.data["result"]
    assert data["dimension"] == first_dim
    assert "element_counts" in data
    assert "level_count" in data


# ── get_leaf_elements ───────────────────────────────────────────────────

async def test_get_leaf_elements(mcp_client: Client[FastMCPTransport]):
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    first_dim = dims.data["result"][0]

    result = await mcp_client.call_tool(
        "get_leaf_elements",
        {"instance": INSTANCE, "dimension_name": first_dim, "sample": 5},
    )
    data = result.data["result"]
    assert data["dimension"] == first_dim
    assert "leaf_elements" in data
    assert "total" in data


async def test_get_leaf_elements_with_search(
    mcp_client: Client[FastMCPTransport],
):
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    dim = dims.data["result"][0]

    result = await mcp_client.call_tool(
        "get_leaf_elements",
        {
            "instance": INSTANCE,
            "dimension_name": dim,
            "search": "a",
            "sample": 3,
        },
    )
    data = result.data["result"]
    assert "leaf_elements" in data
    for elem in data["leaf_elements"]:
        assert "a" in elem.lower()


# ── expand_element ──────────────────────────────────────────────────────

async def test_expand_element(mcp_client: Client[FastMCPTransport]):
    # Find a dimension with a consolidated element
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    dim = dims.data["result"][0]
    info = await mcp_client.call_tool(
        "get_dimension_info",
        {"instance": INSTANCE, "dimension_name": dim},
    )
    roots = info.data["result"].get("root_elements", [])
    if not roots:
        pytest.skip("No root elements in first dimension")

    # root_elements may be list of dicts or list of strings
    elem_name = roots[0] if isinstance(roots[0], str) else roots[0]["name"]

    result = await mcp_client.call_tool(
        "expand_element",
        {
            "instance": INSTANCE,
            "dimension_name": dim,
            "element_name": elem_name,
            "depth": 1,
        },
    )
    data = result.data["result"]
    assert data["name"] == elem_name
    assert "children" in data


# ── get_parents ─────────────────────────────────────────────────────────

async def test_get_parents(mcp_client: Client[FastMCPTransport], tm1_manager):
    # Create a temp dim with known hierarchy
    dim = "Claude_Test_RO_Parents"
    try:
        tm1_manager.create_dimension(
            dim,
            [
                {"name": "Total", "type": "Consolidated"},
                {"name": "Child1", "type": "Numeric"},
                {"name": "Child2", "type": "Numeric"},
            ],
            edges=[
                {"parent": "Total", "child": "Child1", "weight": 1.0},
                {"parent": "Total", "child": "Child2", "weight": 1.0},
            ],
        )
        result = await mcp_client.call_tool(
            "get_parents",
            {
                "instance": INSTANCE,
                "dimension_name": dim,
                "elements": ["Child1", "Child2"],
            },
        )
        data = result.data["result"]
        assert data["parents"]["Child1"] == ["Total"]
        assert data["parents"]["Child2"] == ["Total"]
    finally:
        try:
            tm1_manager.delete_dimension(dim)
        except Exception:
            pass


# ── get_element_attributes ──────────────────────────────────────────────

async def test_get_element_attributes(mcp_client: Client[FastMCPTransport]):
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    dim = dims.data["result"][0]

    result = await mcp_client.call_tool(
        "get_element_attributes",
        {"instance": INSTANCE, "dimension_name": dim},
    )
    data = result.data["result"]
    assert "attributes" in data
    assert "dimension" in data


# ── list_cubes ──────────────────────────────────────────────────────────

async def test_list_cubes(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)


async def test_list_cubes_with_filter(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "list_cubes",
        {"instance": INSTANCE, "filter": "e"},
    )
    data = result.data
    for cube in data["result"]:
        assert "e" in cube.lower()


# ── get_cube ────────────────────────────────────────────────────────────

async def test_get_cube(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]

    result = await mcp_client.call_tool(
        "get_cube",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    data = result.data["result"]
    assert data["name"] == first_cube
    assert "dimensions" in data
    assert isinstance(data["dimensions"], list)


# ── find_cubes_by_dimension ─────────────────────────────────────────────

async def test_find_cubes_by_dimension(
    mcp_client: Client[FastMCPTransport],
):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]
    cube_info = await mcp_client.call_tool(
        "get_cube",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    dim = cube_info.data["result"]["dimensions"][0]

    result = await mcp_client.call_tool(
        "find_cubes_by_dimension",
        {"instance": INSTANCE, "dimension_name": dim},
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)
    assert first_cube in data["result"]


# ── get_cube_rules ──────────────────────────────────────────────────────

async def test_get_cube_rules(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]

    result = await mcp_client.call_tool(
        "get_cube_rules",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    data = result.data
    assert "result" in data
    # rules can be empty string
    assert isinstance(data["result"], str)


# ── list_views ──────────────────────────────────────────────────────────

async def test_list_views(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]

    result = await mcp_client.call_tool(
        "list_views",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    data = result.data
    assert "result" in data
    assert "private" in data["result"]
    assert "public" in data["result"]


# ── get_view_structure ──────────────────────────────────────────────────

async def test_get_view_structure(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]
    views = await mcp_client.call_tool(
        "list_views",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    public_views = views.data["result"]["public"]
    if not public_views:
        pytest.skip("No public views on first cube")

    result = await mcp_client.call_tool(
        "get_view_structure",
        {
            "instance": INSTANCE,
            "cube_name": first_cube,
            "view_name": public_views[0],
        },
    )
    data = result.data
    if "error" in data:
        pytest.skip("View structure not readable")
    assert "result" in data
    assert "name" in data["result"]
    assert "columns" in data["result"]
    assert "rows" in data["result"]


# ── list_subsets ────────────────────────────────────────────────────────

async def test_list_subsets(mcp_client: Client[FastMCPTransport]):
    dims = await mcp_client.call_tool(
        "list_dimensions", {"instance": INSTANCE}
    )
    first_dim = dims.data["result"][0]

    result = await mcp_client.call_tool(
        "list_subsets",
        {"instance": INSTANCE, "dimension_name": first_dim},
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)


# ── get_cell ────────────────────────────────────────────────────────────

async def test_get_cell_error_handling(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "get_cell",
        {
            "instance": INSTANCE,
            "cube_name": "Claude_Test_DoesNotExist",
            "elements": ["Fake"],
        },
    )
    data = result.data
    assert "error" in data


# ── execute_mdx ─────────────────────────────────────────────────────────

async def test_execute_mdx(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    # Pick a cube whose dimensions don't start with '}'
    target_cube = None
    target_dims = None
    for cube_name in cubes.data["result"]:
        info = await mcp_client.call_tool(
            "get_cube",
            {"instance": INSTANCE, "cube_name": cube_name},
        )
        dims = info.data["result"]["dimensions"]
        if len(dims) >= 2 and not any(d.startswith("}") for d in dims):
            target_cube = cube_name
            target_dims = dims
            break

    if target_cube is None:
        pytest.skip("No cube with 2+ non-control dimensions")

    d1, d2 = target_dims[0], target_dims[1]
    mdx = (
        f"SELECT "
        f"{{[{d1}].[{d1}].Members}} ON 0, "
        f"{{[{d2}].[{d2}].Members}} ON 1 "
        f"FROM [{target_cube}]"
    )

    result = await mcp_client.call_tool(
        "execute_mdx",
        {"instance": INSTANCE, "mdx": mdx, "top": 1},
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)


# ── execute_view_query ──────────────────────────────────────────────────

async def test_execute_view_query(mcp_client: Client[FastMCPTransport]):
    cubes = await mcp_client.call_tool(
        "list_cubes", {"instance": INSTANCE}
    )
    first_cube = cubes.data["result"][0]
    views = await mcp_client.call_tool(
        "list_views",
        {"instance": INSTANCE, "cube_name": first_cube},
    )
    public_views = views.data["result"]["public"]
    if not public_views:
        pytest.skip("No public views to execute")

    result = await mcp_client.call_tool(
        "execute_view_query",
        {
            "instance": INSTANCE,
            "cube_name": first_cube,
            "view_name": public_views[0],
            "top": 1,
        },
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)


# ── list_processes ──────────────────────────────────────────────────────

async def test_list_processes(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "list_processes", {"instance": INSTANCE}
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)


async def test_list_processes_with_filter(
    mcp_client: Client[FastMCPTransport],
):
    result = await mcp_client.call_tool(
        "list_processes",
        {"instance": INSTANCE, "filter": "a"},
    )
    data = result.data
    for proc in data["result"]:
        assert "a" in proc.lower()


# ── get_process_template ────────────────────────────────────────────────

async def test_get_process_template(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool("get_process_template", {})
    data = result.data["result"]
    for key in [
        "name", "prolog_procedure", "metadata_procedure",
        "data_procedure", "epilog_procedure", "parameters", "variables",
    ]:
        assert key in data


# ── get_process_error_log ───────────────────────────────────────────────

async def test_get_process_error_log_nonexistent(
    mcp_client: Client[FastMCPTransport],
):
    result = await mcp_client.call_tool(
        "get_process_error_log",
        {"instance": INSTANCE, "process_name": "Claude_Test_DoesNotExist"},
    )
    data = result.data
    assert "error" in data


# ── search_processes ────────────────────────────────────────────────────

async def test_search_processes(mcp_client: Client[FastMCPTransport]):
    result = await mcp_client.call_tool(
        "search_processes",
        {"instance": INSTANCE, "keyword": "a"},
    )
    data = result.data
    assert "result" in data
    assert isinstance(data["result"], list)
    for entry in data["result"]:
        assert "name" in entry
        assert "match_type" in entry
