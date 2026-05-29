"""TM1 MCP Server — FastMCP server exposing TM1 exploration and TI Process tools.

Usage:
    python tm1-mcp-server/tm1_mcp_tool.py

Communicates via stdio with the MCP host (Claude Code).
"""

import json
import sys
from functools import wraps
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context

from tm1_connector import TM1Manager, TM1OperationError


def _coerce_str_to_list(value: list[dict[str, Any]] | str | None) -> list[dict[str, Any]] | None:
    """Auto-parse JSON-string inputs for list[dict] parameters.

    MCP clients (e.g. Claude Code) may serialize complex-typed parameters
    (list[dict]) as JSON strings instead of native JSON arrays. This helper
    transparently converts such string inputs back to lists so Pydantic
    validation passes.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return value
    return value

RO = {"readOnlyHint": True}
IDEMPOTENT = {"idempotentHint": True}
DESTRUCTIVE = {"destructiveHint": True}

mcp = FastMCP(
    "TM1 Explorer & Process Manager",
    instructions=(
        "Tools for exploring IBM TM1 instances (Dimensions, Cubes, Views, "
        "Subsets, Cells) and managing TI Processes (CRUD + execute). "
        "All tools require an 'instance' parameter to select which TM1 server "
        "to connect to. Use list_instances() to see available servers. "
        "Read-only tools are marked with readOnlyHint. "
        "delete_process is the only destructive tool."
    ),
    version="1.0.0",
)


# ======================================================================
# Utility
# ======================================================================

def _call(instance: str) -> TM1Manager:
    """Create a TM1Manager context manager for a tool call."""
    return TM1Manager.call(instance)  # type: ignore[no-any-return]


def _ok(result: Any) -> dict[str, Any]:
    """Wrap a plain result in a success dict."""
    return {"result": result}


def _handle_error(exc: Exception, operation: str) -> dict[str, Any]:
    """Convert exceptions to user-friendly error dicts."""
    if isinstance(exc, TM1OperationError):
        return {"error": str(exc), "error_source": "tm1_server", "operation": operation}
    return {"error": str(exc), "error_source": "local", "operation": operation}


def _mcp_tool(operation: str):
    """Decorator that wraps MCP tool calls with unified error handling."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                return _handle_error(exc, operation)
        return wrapper
    return decorator


# ======================================================================
# Instance
# ======================================================================

@mcp.tool(annotations=IDEMPOTENT)
def list_instances() -> list[str]:
    """List all configured TM1 instance names from config/tm1py_config.ini.

    Typically the first tool to call — most other tools require an
    ``instance`` parameter returned by this function.

    Returns:
        Sorted list of TM1 instance names, e.g. ["FDI", "Planning"].
    """
    return TM1Manager.list_instances()


# ======================================================================
# Dimension tools (read-only)
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("list_dimensions")
def list_dimensions(
    instance: str,
    filter: str | None = None,
    skip_control_dims: bool = True,
) -> dict[str, Any]:
    """List dimension names. Control dims (``}`` prefix) excluded by default.

    Args:
        instance: TM1 instance name.
        filter: Case-insensitive keyword to filter names.
        skip_control_dims: Exclude control dimensions. Default True.

    Returns:
        ``{"result": [dim_name, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        dims = tm1.list_dimensions(skip_control_dims=skip_control_dims)
    if filter:
        kw = filter.lower()
        dims = [d for d in dims if kw in d.lower()]
    return _ok(dims)


@mcp.tool(annotations=RO)
@_mcp_tool("get_dimension_info")
def get_dimension_info(
    instance: str,
    dimension_name: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Get dimension overview: element counts (N/S/C), levels, attributes, root elements.

    Recommended first step when exploring a dimension to understand its
    scale and structure.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to inspect.
        hierarchy: Hierarchy name; defaults to first hierarchy.

    Returns:
        ``{"result": {dimension, hierarchy, element_counts, level_count,
        attribute_names, root_elements}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.get_dimension_info(dimension_name, hierarchy_name=hierarchy)
        )


@mcp.tool(annotations=RO)
@_mcp_tool("get_leaf_elements")
def get_leaf_elements(
    instance: str,
    dimension_name: str,
    hierarchy: str | None = None,
    under: str | None = None,
    search: str | None = None,
    sample: int | None = None,
) -> dict[str, Any]:
    """Get leaf (N/S) elements, excluding Consolidated.

    Common pattern: ``get_leaf_elements(under="Total Revenue")`` to scope
    to a consolidation's leaf descendants. Helps Agent understand dimension
    granularity before writing TI code or constructing Subset/View data sources.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to query.
        hierarchy: Hierarchy name; defaults to first hierarchy.
        under: Parent element — only leaf descendants returned.
        search: Case-insensitive keyword to filter element names.
        sample: Max elements to return; sets ``truncated=True`` if exceeded.

    Returns:
        ``{"result": {dimension, hierarchy, under, leaf_elements, total,
        truncated}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.get_leaf_elements(
                dimension_name,
                hierarchy_name=hierarchy,
                under=under,
                search=search,
                sample=sample,
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("expand_element")
def expand_element(
    instance: str,
    dimension_name: str,
    element_name: str,
    hierarchy: str | None = None,
    depth: int | None = 1,
    include_attributes: bool = False,
) -> dict[str, Any]:
    """Expand an element to inspect its children hierarchy tree.

    Drill down into consolidation structure progressively: depth=1 for
    immediate children, None for full subtree.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension containing the element.
        element_name: Element to expand.
        hierarchy: Hierarchy name; defaults to first hierarchy.
        depth: Levels to expand. 1=children, None=full subtree. Default 1.
        include_attributes: Include attribute values for root element. Default False.

    Returns:
        ``{"result": {dimension, hierarchy, depth_limit, name, type,
        children?, attributes?}}`` — children are recursive node dicts.
        Or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.expand_element(
                dimension_name,
                element_name,
                hierarchy_name=hierarchy,
                depth=depth,
                include_attributes=include_attributes,
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("get_parents")
def get_parents(
    instance: str,
    dimension_name: str,
    elements: list[str],
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Get immediate parent consolidations for given elements.

    Essential before modifying hierarchy — know which parent(s) an element
    belongs to.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to query.
        elements: Element names to look up parents for.
        hierarchy: Hierarchy name; defaults to first hierarchy.

    Returns:
        ``{"result": {dimension, hierarchy, parents: {elem: [parent, ...]}}}``
        or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.get_parents(dimension_name, elements, hierarchy_name=hierarchy)
        )


@mcp.tool(annotations=RO)
@_mcp_tool("get_element_attributes")
def get_element_attributes(
    instance: str,
    dimension_name: str,
    hierarchy: str | None = None,
    elements: list[str] | None = None,
    attribute_names: list[str] | None = None,
) -> dict[str, Any]:
    """Get element attribute values (aliases, descriptions, etc.).

    Always specify ``elements`` to scope results — full-dimension retrieval
    can be slow on large dimensions.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to query.
        hierarchy: Hierarchy name; defaults to first hierarchy.
        elements: Element names to scope; all elements if None.
        attribute_names: Attribute names to retrieve; all if None.

    Returns:
        ``{"result": {dimension, hierarchy,
        attributes: {elem: {attr: value}}}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.get_element_attributes(
                dimension_name,
                hierarchy_name=hierarchy,
                elements=elements,
                attribute_names=attribute_names,
            )
        )


# ======================================================================
# Cube tools (read-only)
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("list_cubes")
def list_cubes(
    instance: str,
    filter: str | None = None,
    skip_control_cubes: bool = True,
) -> dict[str, Any]:
    """List cube names. Control cubes (``}`` prefix) excluded by default.

    Args:
        instance: TM1 instance name.
        filter: Case-insensitive keyword to filter names.
        skip_control_cubes: Exclude control cubes. Default True.

    Returns:
        ``{"result": [cube_name, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        cubes = tm1.list_cubes(skip_control_cubes=skip_control_cubes)
    if filter:
        kw = filter.lower()
        cubes = [c for c in cubes if kw in c.lower()]
    return _ok(cubes)


@mcp.tool(annotations=RO)
@_mcp_tool("get_cube")
def get_cube(instance: str, cube_name: str) -> dict[str, Any]:
    """Get cube structure: dimension order, last update, rules errors.

    Critical for TI development — CellPutN/CellPutS parameters must follow
    the cube's dimension order returned in ``dimensions``.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to inspect.

    Returns:
        ``{"result": {name, dimensions, last_data_update, rules_errors}}``
        or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_cube(cube_name))


@mcp.tool(annotations=RO)
@_mcp_tool("find_cubes_by_dimension")
def find_cubes_by_dimension(
    instance: str,
    dimension_name: str,
    skip_control_cubes: bool = True,
) -> dict[str, Any]:
    """Find cubes using a specific dimension. Useful for impact analysis.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to search for.
        skip_control_cubes: Exclude control cubes. Default True.

    Returns:
        ``{"result": [cube_name, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.find_cubes_using_dimension(
                dimension_name, skip_control_cubes=skip_control_cubes
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("get_cube_rules")
def get_cube_rules(instance: str, cube_name: str) -> dict[str, Any]:
    """Get full rules text of a cube. Empty string if no rules.

    Args:
        instance: TM1 instance name.
        cube_name: Cube whose rules to retrieve.

    Returns:
        ``{"result": "<rules_text>"}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_cube_rules(cube_name))


# ======================================================================
# View tools (read-only)
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("list_views")
def list_views(instance: str, cube_name: str) -> dict[str, Any]:
    """List private and public view names for a cube.

    Args:
        instance: TM1 instance name.
        cube_name: Cube whose views to list.

    Returns:
        ``{"result": {private: [...], public: [...]}} or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.list_views(cube_name))


@mcp.tool(annotations=RO)
@_mcp_tool("get_view_structure")
def get_view_structure(
    instance: str,
    cube_name: str,
    view_name: str,
    private: bool = False,
) -> dict[str, Any]:
    """Get view axis layout: columns/rows/titles with dim-subset-element details.

    Each axis entry includes: dimension, subset, subset_type (static/dynamic),
    expression (dynamic), elements (static), selected_element (titles).

    Args:
        instance: TM1 instance name.
        cube_name: Cube containing the view.
        view_name: View to inspect.
        private: True for private view. Default False.

    Returns:
        ``{"result": {name, cube, private, columns, rows, titles,
        suppress_empty_rows, suppress_empty_columns}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_view_structure(cube_name, view_name, private=private))


# ======================================================================
# Subset tools (read-only)
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("list_subsets")
def list_subsets(
    instance: str,
    dimension_name: str,
    hierarchy: str | None = None,
    private: bool = False,
) -> dict[str, Any]:
    """List subset names for a dimension.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension whose subsets to list.
        hierarchy: Hierarchy name; defaults to first hierarchy.
        private: True for private subsets. Default False.

    Returns:
        ``{"result": [subset_name, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.list_subsets(
                dimension_name, hierarchy_name=hierarchy, private=private
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("get_subset")
def get_subset(
    instance: str,
    dimension_name: str,
    subset_name: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Get subset details: type (static/dynamic), elements, MDX expression.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension containing the subset.
        subset_name: Subset to retrieve.
        hierarchy: Hierarchy name; defaults to first hierarchy.

    Returns:
        ``{"result": {name, dimension, hierarchy, private, subset_type,
        element_count, elements, expression?}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.get_subset(dimension_name, subset_name, hierarchy_name=hierarchy)
        )


# ======================================================================
# Cell tools (read-only)
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("get_cell")
def get_cell(
    instance: str,
    cube_name: str,
    elements: list[str],
) -> dict[str, Any]:
    """Get a single cell value. Elements must follow cube's dimension order.

    Use ``get_cube`` first to confirm dimension order.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to read from.
        elements: Element names in cube's dimension order.

    Returns:
        ``{"result": <value>}`` (str or float) or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_cell_value(cube_name, elements))


@mcp.tool(annotations=RO)
@_mcp_tool("execute_mdx")
def execute_mdx(
    instance: str,
    mdx: str,
    top: int | None = None,
    skip_zeros: bool = True,
    skip_consolidated: bool = False,
    use_blob: bool = False
) -> dict[str, Any]:
    """Execute MDX query, return results as list of record dicts.

    For flexible ad-hoc data retrieval beyond single-cell lookups or
    predefined views.

    Args:
        instance: TM1 instance name.
        mdx: Valid TM1 MDX query string.
        top: Max rows to return.
        skip_zeros: Exclude zero-value cells. Default True.
        skip_consolidated: Exclude consolidated cells. Default False.
        use_blob: Use blob transfer for large results. Default False.

    Returns:
        ``{"result": [{dim_elem: value, ...}, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.execute_mdx(
                mdx,
                top=top,
                skip_zeros=skip_zeros,
                skip_consolidated=skip_consolidated,
                use_blob=use_blob
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("execute_view_query")
def execute_view_query(
    instance: str,
    cube_name: str,
    view_name: str,
    private: bool = False,
    top: int | None = None,
) -> dict[str, Any]:
    """Execute a named view, return cell data as list of record dicts.

    Like ``execute_mdx`` but uses a pre-defined view.

    Args:
        instance: TM1 instance name.
        cube_name: Cube containing the view.
        view_name: View to execute.
        private: True for private view. Default False.
        top: Max rows to return.

    Returns:
        ``{"result": [{dim_elem: value, ...}, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.execute_view(cube_name, view_name, private=private, top=top))


# ======================================================================
# Process tools — read
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("list_processes")
def list_processes(
    instance: str,
    filter: str | None = None,
    skip_control_processes: bool = True,
) -> dict[str, Any]:
    """List TI process names. Control processes (``}`` prefix) excluded by default.

    Args:
        instance: TM1 instance name.
        filter: Case-insensitive keyword to filter names.
        skip_control_processes: Exclude control processes. Default True.

    Returns:
        ``{"result": [process_name, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        procs = tm1.list_processes(skip_control_processes=skip_control_processes)
    if filter:
        kw = filter.lower()
        procs = [p for p in procs if kw in p.lower()]
    return _ok(procs)


@mcp.tool(annotations=RO)
@_mcp_tool("get_process")
def get_process(
    instance: str,
    process_name: str,
    include_code: bool = True,
) -> dict[str, Any]:
    """Get TI process details: parameters, variables, datasource, and code.

    Primary tool for reviewing a process before modifying it.

    Args:
        instance: TM1 instance name.
        process_name: Process to retrieve.
        include_code: Include all four tab source code. Default True.

    Returns:
        ``{"result": {name, datasource_type, has_security_access,
        parameters, variables, prolog_procedure?, metadata_procedure?,
        data_procedure?, epilog_procedure?}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_process(process_name, include_code=include_code))


@mcp.tool(annotations=RO)
@_mcp_tool("search_processes")
def search_processes(
    instance: str,
    keyword: str,
    search_code: bool = True,
) -> dict[str, Any]:
    """Search processes by name and optionally code content.

    Returns matches with match_type: "name" or "code" indicating where
    the keyword was found.

    Args:
        instance: TM1 instance name.
        keyword: Case-insensitive search keyword.
        search_code: Also search within source code. Default True.

    Returns:
        ``{"result": [{name, match_type}, ...]}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.search_processes(keyword, search_code=search_code))


@mcp.tool(annotations=RO)
@_mcp_tool("compile_process")
def compile_process(instance: str, process_name: str) -> dict[str, Any]:
    """Compile a TI process and return syntax errors (no execution).

    Use after create/update to validate code before executing.

    Args:
        instance: TM1 instance name.
        process_name: Process to compile.

    Returns:
        ``{"result": {process_name, has_errors, errors}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.compile_process(process_name))


@mcp.tool(annotations=RO)
@_mcp_tool("get_process_error_log")
def get_process_error_log(instance: str, process_name: str) -> dict[str, Any]:
    """Get most recent error log message for a TI process.

    Use after execution failure to diagnose errors.

    Args:
        instance: TM1 instance name.
        process_name: Process whose error log to retrieve.

    Returns:
        ``{"result": "<error_message>"}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.get_process_error_log(process_name))


# ======================================================================
# Process tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("create_process")
def create_process(
    instance: str,
    process_name: str,
    prolog: str = "",
    metadata: str = "",
    data: str = "",
    epilog: str = "",
    parameters: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
    datasource_type: str = "None",
) -> dict[str, Any]:
    """Create a new TI process with four code tabs, parameters, and variables.

    Args:
        instance: TM1 instance name.
        process_name: Unique process name (alphanumeric + underscores).
        prolog: Prolog tab code — runs once before datasource. Default "".
        metadata: Metadata tab code — runs per record, for dimension ops. Default "".
        data: Data tab code — runs per record, for cell writes. Default "".
        epilog: Epilog tab code — runs once after all records. Default "".
        parameters: List of dicts with keys name, prompt?, value, type("String"/"Numeric").
        variables: List of dicts with keys name, type("String"/"Numeric").
        datasource_type: "None", "ASCII", "ODBC", "TM1CubeView". Default "None".

    Returns:
        ``{"result": {success, process_name}}`` or ``{"error": ...}``.
    """
    parameters = _coerce_str_to_list(parameters)
    variables = _coerce_str_to_list(variables)
    with _call(instance) as tm1:
        return _ok(
            tm1.create_process(
                process_name=process_name,
                prolog=prolog,
                metadata=metadata,
                data=data,
                epilog=epilog,
                parameters=parameters,
                variables=variables,
                datasource_type=datasource_type,
            )
        )


@mcp.tool
@_mcp_tool("update_process")
def update_process(
    instance: str,
    process_name: str,
    prolog: str | None = None,
    metadata: str | None = None,
    data: str | None = None,
    epilog: str | None = None,
    parameters: list[dict[str, Any]] | None = None,
    variables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Partial update of an existing TI process. None = keep unchanged.

    Warning: providing parameters/variables replaces the entire list (not merge).
    Use ``get_process`` first to inspect current state.

    Args:
        instance: TM1 instance name.
        process_name: Process to update.
        prolog: New Prolog code, or None to keep.
        metadata: New Metadata code, or None to keep.
        data: New Data code, or None to keep.
        epilog: New Epilog code, or None to keep.
        parameters: Replacement list (same format as create_process), or None.
        variables: Replacement list (same format as create_process), or None.

    Returns:
        ``{"result": {success, process_name}}`` or ``{"error": ...}``.
    """
    parameters = _coerce_str_to_list(parameters)
    variables = _coerce_str_to_list(variables)
    with _call(instance) as tm1:
        return _ok(
            tm1.update_process(
                process_name=process_name,
                prolog=prolog,
                metadata=metadata,
                data=data,
                epilog=epilog,
                parameters=parameters,
                variables=variables,
            )
        )


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_process")
def delete_process(instance: str, process_name: str) -> dict[str, Any]:
    """Permanently delete a TI process. Cannot be undone.

    Args:
        instance: TM1 instance name.
        process_name: Process to delete.

    Returns:
        ``{"result": {success, process_name}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.delete_process(process_name))


@mcp.tool
async def execute_process(
    instance: str,
    process_name: str,
    parameters: list[dict[str, Any]] | None = None,
    timeout: int | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Execute a TI process with optional parameters and timeout.

    Args:
        instance: TM1 instance name.
        process_name: Process to execute.
        parameters: Runtime params as [{"name": "pX", "value": "..."}].
        timeout: Timeout in seconds; None = server default.
        ctx: Internal FastMCP context. Do not set.

    Returns:
        ``{"result": {success, status, process_name,
        error_log_file?, error_log?}}`` or ``{"error": ...}``.
    """
    parameters = _coerce_str_to_list(parameters)
    try:
        if ctx:
            await ctx.info(f"Executing '{process_name}' on {instance}...")
        with _call(instance) as tm1:
            result = tm1.execute_process(
                process_name, parameters=parameters, timeout=timeout
            )
        if ctx:
            if result["success"]:
                await ctx.info(
                    f"'{process_name}' completed: {result.get('status', 'OK')}"
                )
            else:
                await ctx.warning(
                    f"'{process_name}' failed: {result.get('error_log', 'unknown')}"
                )
        return _ok(result)
    except Exception as exc:
        return _handle_error(exc, f"execute_process({process_name})")


@mcp.tool(annotations=IDEMPOTENT)
def get_process_template() -> dict[str, Any]:
    """Return empty TI process template structure for reference.

    Use as starting point when creating a new process.

    Returns:
        ``{"result": {name, datasource_type, has_security_access,
        parameters, variables, prolog_procedure, metadata_procedure,
        data_procedure, epilog_procedure}}``.
    """
    return _ok(TM1Manager.get_process_template())


# ======================================================================
# Dimension tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("create_dimension")
def create_dimension(
    instance: str,
    dimension_name: str,
    elements: list[dict[str, Any]],
    edges: list[dict[str, Any]] | None = None,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Create a new dimension with elements and hierarchy.

    Args:
        instance: TM1 instance name.
        dimension_name: Name for the new dimension.
        elements: List of element dicts with keys "name" and "type"
                  ("Numeric", "String", "Consolidated").
        edges: List of edge dicts with keys "parent", "child", "weight".
               weight defaults to 1.0.
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "element_count"}}`` or ``{"error": ...}``.
    """
    elements = _coerce_str_to_list(elements)
    edges = _coerce_str_to_list(edges)
    with _call(instance) as tm1:
        return _ok(
            tm1.create_dimension(
                dimension_name, elements=elements, edges=edges,
                hierarchy_name=hierarchy,
            )
        )


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_dimension")
def delete_dimension(instance: str, dimension_name: str) -> dict[str, Any]:
    """Permanently delete a dimension and all its elements. Cannot be undone.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to delete.

    Returns:
        ``{"result": {"success", "dimension_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.delete_dimension(dimension_name))


@mcp.tool
@_mcp_tool("add_elements")
def add_elements(
    instance: str,
    dimension_name: str,
    elements: list[dict[str, Any]],
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Add elements to an existing dimension.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to add elements to.
        elements: List of element dicts with keys "name" and "type"
                  ("Numeric", "String", "Consolidated").
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "added_count"}}`` or ``{"error": ...}``.
    """
    elements = _coerce_str_to_list(elements)
    with _call(instance) as tm1:
        return _ok(
            tm1.add_elements(
                dimension_name, elements=elements, hierarchy_name=hierarchy,
            )
        )


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_elements")
def delete_elements(
    instance: str,
    dimension_name: str,
    element_names: list[str],
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Remove elements from a dimension. Cannot be undone.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to remove elements from.
        element_names: Names of elements to delete.
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "deleted_count"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.delete_elements(
                dimension_name, element_names=element_names,
                hierarchy_name=hierarchy,
            )
        )


@mcp.tool
@_mcp_tool("update_hierarchy")
def update_hierarchy(
    instance: str,
    dimension_name: str,
    add_edges: list[dict[str, Any]] | None = None,
    remove_edges: list[dict[str, Any]] | None = None,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Add or remove consolidation edges in a dimension hierarchy.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension whose hierarchy to update.
        add_edges: Edge dicts with keys "parent", "child", "weight" (default 1.0).
        remove_edges: Edge dicts with keys "parent", "child".
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "edges_added", "edges_removed"}}``
        or ``{"error": ...}``.
    """
    add_edges = _coerce_str_to_list(add_edges)
    remove_edges = _coerce_str_to_list(remove_edges)
    with _call(instance) as tm1:
        return _ok(
            tm1.update_hierarchy(
                dimension_name, add_edges=add_edges,
                remove_edges=remove_edges, hierarchy_name=hierarchy,
            )
        )


@mcp.tool
@_mcp_tool("create_element_attribute")
def create_element_attribute(
    instance: str,
    dimension_name: str,
    attribute_name: str,
    attribute_type: str = "String",
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Create a new element attribute column on a dimension.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to add attribute to.
        attribute_name: Name of the new attribute.
        attribute_type: "String", "Numeric", or "Alias". Default "String".
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "attribute_name", "attribute_type"}}``
        or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.create_element_attribute(
                dimension_name, attribute_name=attribute_name,
                attribute_type=attribute_type, hierarchy_name=hierarchy,
            )
        )


@mcp.tool
@_mcp_tool("write_element_attributes")
def write_element_attributes(
    instance: str,
    dimension_name: str,
    attribute_values: list[dict[str, Any]],
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Write attribute values for elements in a dimension.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension whose elements to update.
        attribute_values: List of dicts with keys "element", "attribute", "value".
                          e.g. [{"element": "Q1", "attribute": "Alias", "value": "Quarter 1"}]
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "values_updated"}}`` or ``{"error": ...}``.
    """
    attribute_values = _coerce_str_to_list(attribute_values)
    with _call(instance) as tm1:
        return _ok(
            tm1.write_element_attributes(
                dimension_name, attribute_values=attribute_values,
                hierarchy_name=hierarchy,
            )
        )


# ======================================================================
# File-based dimension tools — write (for large specs)
# ======================================================================

@mcp.tool
@_mcp_tool("create_dimension_file")
def create_dimension_file(
    instance: str,
    file_path: str,
) -> dict[str, Any]:
    """Create a full dimension from a spec JSON file (elements, edges, attributes, subsets).

    Reads a dimension-spec.json from disk, so payload size is unlimited.
    Path is relative to the project root directory.

    Args:
        instance: TM1 instance name.
        file_path: Path to the spec JSON file (relative to project root or absolute).

    Returns:
        ``{"result": {"success", "dimension_name", "element_count", "attributes_created", "attribute_values_written", "subsets_created"}}``
        or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.create_dimension_from_file(file_path))


@mcp.tool
@_mcp_tool("add_elements_file")
def add_elements_file(
    instance: str,
    dimension_name: str,
    file_path: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Add elements to an existing dimension from a JSON file.

    File format: ``[{"name": "...", "type": "..."}]`` or ``{"elements": [...]}``.
    Path is relative to the project root directory.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to add elements to.
        file_path: Path to the JSON file (relative to project root or absolute).
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "added_count"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.add_elements_from_file(
                file_path, dimension_name, hierarchy_name=hierarchy,
            )
        )


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("update_hierarchy_file")
def update_hierarchy_file(
    instance: str,
    dimension_name: str,
    file_path: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Add or remove consolidation edges from a JSON file.

    File format: ``{"add_edges": [...], "remove_edges": [...]}``.
    Path is relative to the project root directory.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension whose hierarchy to update.
        file_path: Path to the JSON file (relative to project root or absolute).
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "edges_added", "edges_removed"}}``
        or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.update_hierarchy_from_file(
                file_path, dimension_name, hierarchy_name=hierarchy,
            )
        )


@mcp.tool
@_mcp_tool("write_element_attributes_file")
def write_element_attributes_file(
    instance: str,
    dimension_name: str,
    file_path: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Write attribute values for elements from a JSON file.

    File format: ``[{"element": "...", "attribute": "...", "value": "..."}]``
    or ``{"attribute_values": [...]}``.
    Path is relative to the project root directory.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension whose elements to update.
        file_path: Path to the JSON file (relative to project root or absolute).
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "dimension_name", "values_updated"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.write_element_attributes_from_file(
                file_path, dimension_name, hierarchy_name=hierarchy,
            )
        )


# ======================================================================
# Subset tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("create_subset")
def create_subset(
    instance: str,
    dimension_name: str,
    subset_name: str,
    hierarchy: str | None = None,
    elements: list[str] | None = None,
    expression: str | None = None,
) -> dict[str, Any]:
    """Create a static or dynamic (MDX) subset on a dimension.

    Provide ``elements`` for a static subset, or ``expression`` for an MDX dynamic subset.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to create subset on.
        subset_name: Name for the new subset.
        hierarchy: Hierarchy name; defaults to dimension_name.
        elements: Element names for a static subset.
        expression: MDX expression for a dynamic subset.

    Returns:
        ``{"result": {"success", "subset_name", "dimension_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.create_subset(
                dimension_name, subset_name, hierarchy_name=hierarchy,
                elements=elements, expression=expression,
            )
        )


@mcp.tool
@_mcp_tool("update_subset")
def update_subset(
    instance: str,
    dimension_name: str,
    subset_name: str,
    hierarchy: str | None = None,
    elements: list[str] | None = None,
    expression: str | None = None,
) -> dict[str, Any]:
    """Update an existing subset's elements or MDX expression.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension containing the subset.
        subset_name: Subset to update.
        hierarchy: Hierarchy name; defaults to dimension_name.
        elements: New element list for static subset.
        expression: New MDX expression for dynamic subset.

    Returns:
        ``{"result": {"success", "subset_name", "dimension_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.update_subset(
                dimension_name, subset_name, hierarchy_name=hierarchy,
                elements=elements, expression=expression,
            )
        )


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_subset")
def delete_subset(
    instance: str,
    dimension_name: str,
    subset_name: str,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Delete a subset from a dimension. Cannot be undone.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension containing the subset.
        subset_name: Subset to delete.
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"success", "subset_name", "dimension_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.delete_subset(
                dimension_name, subset_name, hierarchy_name=hierarchy,
            )
        )


# ======================================================================
# Cube tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("create_cube")
def create_cube(
    instance: str,
    cube_name: str,
    dimensions: list[str],
) -> dict[str, Any]:
    """Create a new cube with ordered dimensions.

    Args:
        instance: TM1 instance name.
        cube_name: Name for the new cube.
        dimensions: Dimension names in the desired order.

    Returns:
        ``{"result": {"success", "cube_name", "dimensions"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.create_cube(cube_name, dimensions))


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_cube")
def delete_cube(instance: str, cube_name: str) -> dict[str, Any]:
    """Permanently delete a cube and all its data. Cannot be undone.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to delete.

    Returns:
        ``{"result": {"success", "cube_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.delete_cube(cube_name))


# ======================================================================
# View tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("create_view")
def create_view(
    instance: str,
    cube_name: str,
    view_name: str,
    mdx: str,
) -> dict[str, Any]:
    """Create an MDX view on a cube.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to create the view on.
        view_name: Name for the new view.
        mdx: Valid MDX query string defining the view.

    Returns:
        ``{"result": {"success", "view_name", "cube_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.create_view(cube_name, view_name, mdx))


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("delete_view")
def delete_view(
    instance: str,
    cube_name: str,
    view_name: str,
    private: bool = False,
) -> dict[str, Any]:
    """Delete a view from a cube. Cannot be undone.

    Args:
        instance: TM1 instance name.
        cube_name: Cube containing the view.
        view_name: View to delete.
        private: True for private view. Default False.

    Returns:
        ``{"result": {"success", "view_name", "cube_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.delete_view(cube_name, view_name, private=private))


# ======================================================================
# Cell tools — write
# ======================================================================

@mcp.tool
@_mcp_tool("write_cell")
def write_cell(
    instance: str,
    cube_name: str,
    elements: list[str],
    value: float | str,
) -> dict[str, Any]:
    """Write a single cell value. Elements must follow cube's dimension order.

    Use ``get_cube`` first to confirm dimension order.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to write to.
        elements: Element names in cube's dimension order.
        value: Numeric or string value to write.

    Returns:
        ``{"result": {"success", "cube_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.write_cell(cube_name, elements, value))


@mcp.tool
@_mcp_tool("write_bulk")
def write_bulk(
    instance: str,
    cube_name: str,
    cellset: dict[str, Any],
    dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Bulk write multiple cells to a cube.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to write to.
        cellset: Dict mapping element-tuple strings to values.
                 Keys like "('Dim1Elem','Dim2Elem')", values are numbers/strings.
        dimensions: Dimension names in order; auto-detected if None.

    Returns:
        ``{"result": {"success", "cube_name", "cells_written"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.write_bulk(cube_name, cellset, dimensions=dimensions))


@mcp.tool
@_mcp_tool("write_file")
def write_file(
    instance: str,
    cube_name: str,
    file_path: str,
    dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Read a CSV file and write its data to a cube.

    CSV column order should match cube dimension order, with the last column as values.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to write to.
        file_path: Local path to CSV file.
        dimensions: Dimension names in order; auto-detected if None.

    Returns:
        ``{"result": {"success", "cube_name", "rows_written"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.write_file(cube_name, file_path, dimensions=dimensions))


@mcp.tool(annotations=DESTRUCTIVE)
@_mcp_tool("clear_cube")
def clear_cube(
    instance: str,
    cube_name: str,
    mdx_filter: str | None = None,
) -> dict[str, Any]:
    """Clear cube data. Optionally clear only a slice matching MDX filter. Cannot be undone.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to clear.
        mdx_filter: MDX expression to scope the clear. None = clear entire cube.

    Returns:
        ``{"result": {"success", "cube_name"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(tm1.clear_cube(cube_name, mdx_filter=mdx_filter))


# ======================================================================
# Verification tools
# ======================================================================

@mcp.tool(annotations=RO)
@_mcp_tool("verify_dimension")
def verify_dimension(
    instance: str,
    dimension_name: str,
    expected_elements: dict[str, int] | None = None,
    expected_attributes: list[str] | None = None,
    hierarchy: str | None = None,
) -> dict[str, Any]:
    """Verify dimension structure matches expectations.

    Args:
        instance: TM1 instance name.
        dimension_name: Dimension to verify.
        expected_elements: Expected element counts by type, e.g. {"Numeric": 5, "Consolidated": 2}.
        expected_attributes: Attribute names that must exist.
        hierarchy: Hierarchy name; defaults to dimension_name.

    Returns:
        ``{"result": {"dimension", "match", "differences", "actual"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.verify_dimension(
                dimension_name,
                expected_elements=expected_elements,
                expected_attributes=expected_attributes,
                hierarchy_name=hierarchy,
            )
        )


@mcp.tool(annotations=RO)
@_mcp_tool("verify_cube")
def verify_cube(
    instance: str,
    cube_name: str,
    expected_dimensions: list[str] | None = None,
    check_has_data: bool = False,
) -> dict[str, Any]:
    """Verify cube structure matches expectations.

    Args:
        instance: TM1 instance name.
        cube_name: Cube to verify.
        expected_dimensions: Expected dimension names in order.
        check_has_data: If True, check that cube contains at least some data.

    Returns:
        ``{"result": {"cube", "match", "differences", "actual"}}`` or ``{"error": ...}``.
    """
    with _call(instance) as tm1:
        return _ok(
            tm1.verify_cube(
                cube_name,
                expected_dimensions=expected_dimensions,
                check_has_data=check_has_data,
            )
        )


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
