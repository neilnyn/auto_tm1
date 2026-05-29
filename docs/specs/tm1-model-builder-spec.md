# Spec: TM1 Model Builder

## Objective

Expand Auto_TM1 from a TI-process-only tool into a full TM1 model construction platform. Add write MCP tools for dimensions, cubes, views, subsets, and data so Claude Code can build, populate, and verify complete TM1 models end-to-end. Plus a unified `tm1-model-builder` skill that orchestrates the full workflow.

**User:** TM1 developers using Claude Code as a force multiplier in dev environments.
**Success looks like:** A developer says "build me a Revenue Planning cube with Account, Period, Scenario dimensions, seed it with FY2024 actuals" and Claude Code does it — dimensions, hierarchies, subsets, cube, views, data — with automatic verification at each step.

## Tech Stack

- Python 3.13 (existing `.venv`)
- TM1py >=2.2.5 (already installed)
- FastMCP 3.2.0 (existing MCP server framework)
- pandas >=3.0.3 (for file-based bulk data reads)
- loguru (existing logging)

## Commands

```bash
# Syntax check MCP server
.venv/Scripts/python -m py_compile tm1_mcp_server/tm1_connector.py
.venv/Scripts/python -m py_compile tm1_mcp_server/tm1_mcp_tool.py

# Run tests (live TM1 connection required, default instance: Neil)
.venv/Scripts/python -m pytest tests/ -v --tb=short

# Single test file
.venv/Scripts/python -m pytest tests/test_dimension_write.py -v --tb=short
```

## Project Structure

```
tm1_mcp_server/
  tm1_connector.py              -- ADD: ~15 write methods to TM1Manager
  tm1_mcp_tool.py               -- ADD: ~18 new @mcp.tool functions

.claude/skills/tm1-model-builder/
  SKILL.md                      -- NEW: router/orchestrator skill definition
  references/
    dimension-ops.md            -- NEW: dimension/subset build patterns
    cube-ops.md                 -- NEW: cube/view build patterns
    data-ops.md                 -- NEW: data read/write patterns
    mcp-tools-reference.md      -- NEW: updated tool reference (write tools)
    coding-conventions.md       -- NEW: shared conventions for model building
  templates/
    dimension-spec.json         -- NEW: dimension specification template
    cube-spec.json              -- NEW: cube specification template

tests/
  conftest.py                   -- EXISTING: session-scoped tm1_manager fixture
  test_dimension_write.py       -- NEW: dimension write tool tests
  test_cube_write.py            -- NEW: cube write tool tests
  test_data_write.py            -- NEW: data write tool tests
  test_subset_write.py          -- NEW: subset write tool tests
  test_view_write.py            -- NEW: view write tool tests
  test_verify.py                -- NEW: verification tool tests

docs/
  specs/
    tm1-model-builder-spec.md   -- THIS FILE
  ideas/
    tm1-model-builder.md        -- IDEA ONE-PAGER (source of truth for vision)
```

## Code Style

Follow existing patterns exactly. New write methods in `tm1_connector.py`:

```python
def create_dimension(self, dimension_name: str, hierarchy_name: str | None,
                     elements: list[dict], edges: list[dict]) -> dict[str, Any]:
    """Create a dimension with elements and hierarchy.

    elements: [{"name": "Total", "type": "Consolidated"}, {"name": "Item1", "type": "Numeric"}]
    edges: [{"parent": "Total", "child": "Item1", "weight": 1.0}]
    """
    try:
        hierarchy_name = hierarchy_name or dimension_name
        from TM1py.Objects import Dimension, Hierarchy, Element

        tm1_elements = [
            Element(name=e["name"], element_type=e["type"])
            for e in elements
        ]
        tm1_edges = {
            (e["parent"], e["child"]): e["weight"]
            for e in edges
        }
        hierarchy = Hierarchy(
            name=hierarchy_name,
            dimension_name=dimension_name,
            elements=tm1_elements,
            edges=tm1_edges if tm1_edges else None,
        )
        dimension = Dimension(name=dimension_name, hierarchies=[hierarchy])
        self.service.dimensions.create(dimension)
        logger.info(f"Created dimension '{dimension_name}' with {len(elements)} elements")
        return {"success": True, "dimension_name": dimension_name,
                "element_count": len(elements)}
    except TM1pyException as exc:
        raise RuntimeError(f"Failed to create dimension '{dimension_name}': {exc}") from exc
```

New MCP tools in `tm1_mcp_tool.py`:

```python
@mcp.tool()
def create_dimension(instance: str, dimension_name: str,
                     elements: list[dict],
                     edges: list[dict] | None = None,
                     hierarchy_name: str | None = None) -> str:
    """Create a new dimension with elements and hierarchy.

    Args:
        instance: TM1 instance name.
        dimension_name: Name for the new dimension.
        elements: List of element dicts with keys "name" and "type"
                  ("Numeric", "String", "Consolidated").
        edges: List of edge dicts with keys "parent", "child", "weight".
               weight defaults to 1.0.
        hierarchy_name: Hierarchy name; defaults to dimension_name.

    Returns:
        {"result": {"success", "dimension_name", "element_count}} or error.
    """
    try:
        with TM1Manager.call(instance) as mgr:
            result = mgr.create_dimension(dimension_name, hierarchy_name, elements, edges or [])
            return _ok(result)
    except Exception as exc:
        return _handle_error(exc, "create dimension")
```

**Key conventions:**
- All new tools use **verb_noun** naming (`create_dimension`, `write_cell`, `clear_cube`)
- Annotation pattern: no annotation for create/update, `DESTRUCTIVE` for delete/clear
- Parameters use plain Python types — no TM1py object types leak into the MCP layer
- `elements` and `edges` are `list[dict]` for JSON serializability across MCP boundary
- Error handling: `try/except` with `RuntimeError` in connector, `_handle_error` in MCP layer
- All write methods return `{"success": True, ...}` on success

## MCP Tools to Implement

### Dimension Write Tools

| Tool | Annotation | TM1Manager Method | TM1py API |
|------|-----------|-------------------|-----------|
| `create_dimension` | — | `create_dimension` | `dimensions.create(Dimension(...))` |
| `delete_dimension` | DESTRUCTIVE | `delete_dimension` | `dimensions.delete(name)` |
| `add_elements` | — | `add_elements` | `elements.add_elements(dim, hier, [Element(...)])` |
| `delete_elements` | DESTRUCTIVE | `delete_elements` | `elements.delete_elements(dim, hier, names)` |
| `update_hierarchy` | — | `update_hierarchy` | `elements.add_edges()` + `elements.delete_edges()` |
| `create_element_attribute` | — | `create_element_attribute` | `elements.create_element_attribute(dim, hier, attr)` |
| `write_element_attributes` | — | `write_element_attributes` | `elements.update_or_create` per element |

### Subset Write Tools

| Tool | Annotation | TM1Manager Method | TM1py API |
|------|-----------|-------------------|-----------|
| `create_subset` | — | `create_subset` | `subsets.create(Subset(...))` |
| `update_subset` | — | `update_subset` | `subsets.update(Subset(...))` |
| `delete_subset` | DESTRUCTIVE | `delete_subset` | `subsets.delete(name, dim, hier)` |

### Cube Write Tools

| Tool | Annotation | TM1Manager Method | TM1py API |
|------|-----------|-------------------|-----------|
| `create_cube` | — | `create_cube` | `cubes.create(Cube(name, dims))` |
| `delete_cube` | DESTRUCTIVE | `delete_cube` | `cubes.delete(name)` |

### View Write Tools

| Tool | Annotation | TM1Manager Method | TM1py API |
|------|-----------|-------------------|-----------|
| `create_view` | — | `create_view` | `views.create(MDXView(...))` |
| `delete_view` | DESTRUCTIVE | `delete_view` | `views.delete(cube, name)` |

### Data Write Tools

| Tool | Annotation | TM1Manager Method | TM1py API |
|------|-----------|-------------------|-----------|
| `write_cell` | — | `write_cell` | `cells.write_value(value, cube, tuple)` |
| `write_bulk` | — | `write_bulk` | `cells.write(cube, dict, ...)` |
| `write_file` | — | `write_file` | `cells.write_dataframe(cube, df, ...)` |
| `clear_cube` | DESTRUCTIVE | `clear_cube` | `cells.clear(cube, **mdx_filters)` |

### Verification Tools

| Tool | Annotation | TM1Manager Method | Purpose |
|------|-----------|-------------------|---------|
| `verify_dimension` | RO | `verify_dimension` | Element counts, hierarchy integrity, attribute coverage |
| `verify_cube` | RO | `verify_cube` | Dimension order, existence, data presence sample |

## Testing Strategy

Tests run against a live TM1 instance (Neil). Each test file follows the existing `conftest.py` fixture pattern.

**Test structure per domain:**
1. **Create** — create an object, verify with existing read tools
2. **Read back** — use existing `get_dimension_info` / `get_cube` to confirm structure
3. **Update** — modify and verify changes
4. **Delete** — clean up, verify deletion
5. **Error cases** — duplicate create, missing dimension, invalid element type

**Coverage expectations:**
- Every write tool gets at least one positive test and one error test
- Verification tools get tests with known-correct and known-incorrect specs
- Cleanup (delete) runs in teardown regardless of test outcome

**Test naming:** `test_<tool_name>_<scenario>` (e.g., `test_create_dimension_with_hierarchy`, `test_write_bulk_from_dict`)

## Boundaries

**Always:**
- Follow existing `TM1Manager` + `@mcp.tool` separation pattern
- Use `DESTRUCTIVE` annotation on all delete/clear tools
- Return structured dicts (`{"success": True, ...}`) from connector methods
- Clean up created objects in test teardown
- Keep TM1py object construction inside `tm1_connector.py` — never leak into MCP layer

**Ask first:**
- Adding new dependencies beyond what's in `pyproject.toml`
- Changing existing read-only tool signatures
- Modifying `conftest.py` or shared test fixtures

**Never:**
- Add sandbox/production safety features (dev-only for now)
- Modify existing read-only tools behavior
- Expose TM1py object types (Element, Hierarchy, etc.) in MCP tool signatures
- Commit with failing tests

## Success Criteria

- [ ] All 18 new MCP tools compile and register without errors
- [ ] `create_dimension` creates a dimension with N/S/C elements and edges, verifiable via `get_dimension_info`
- [ ] `create_cube` creates a cube with correct dimension order, verifiable via `get_cube`
- [ ] `write_cell` writes a value, verifiable via `get_cell`
- [ ] `write_bulk` writes multiple values from a dict, verifiable via `execute_mdx`
- [ ] `write_file` reads a CSV and writes to cube, verifiable via `execute_mdx`
- [ ] `clear_cube` zeros cube data, verifiable via `execute_mdx` returning empty
- [ ] `create_subset` creates both static and MDX subsets, verifiable via `get_subset`
- [ ] `create_view` creates an MDX view, verifiable via `get_view_structure`
- [ ] `verify_dimension` catches mismatched element counts and missing attributes
- [ ] `verify_cube` catches wrong dimension order and missing cubes
- [ ] All `DESTRUCTIVE` tools have the annotation and work correctly
- [ ] `tm1-model-builder` SKILL.md loads without error and routes to correct reference docs
- [ ] End-to-end: build a 3-dimension model with cube, subset, view, and seed data in one session

## Open Questions

None — all resolved in ideation phase. Decisions locked in `docs/ideas/tm1-model-builder.md`.
