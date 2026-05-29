# Implementation Plan: TM1 Model Builder

Source spec: `docs/specs/tm1-model-builder-spec.md`

## Build Order & Dependencies

```
Phase A: Dimension Write          ← foundation, no dependencies
    │
    ├── Phase B: Subset Write     ← depends on A (subsets live in dimensions)
    │
    ├── Phase C: Cube Write       ← depends on A (cubes reference dimensions)
    │       │
    │       ├── Phase D: View Write   ← depends on C (views belong to cubes)
    │       │
    │       └── Phase E: Data Write   ← depends on C (data lives in cubes)
    │
    └── Phase F: Verify Tools     ← depends on A + C (verifies dims & cubes)

Phase G: Skill & References       ← depends on all tools being functional
```

Phases B/C/D can proceed in parallel once A is complete. E/F can proceed once C is complete.

---

## Phase A: Dimension Write Tools

**Why first:** Dimensions are the skeleton. Everything else (subsets, cubes, data) depends on dimensions existing. Validate the write pattern here and the rest follows the same structure.

### A1. Connector methods — `tm1_mcp_server/tm1_connector.py`

Add 7 methods to `TM1Manager` class, after the existing read-only dimension methods (after line ~452):

| Method | TM1py API | Notes |
|--------|-----------|-------|
| `create_dimension(name, hierarchy_name, elements, edges)` | `dimensions.create(Dimension(...))` | Builds Hierarchy + Element objects from list[dict] |
| `delete_dimension(name)` | `dimensions.delete(name)` | Simple wrapper |
| `add_elements(dim, hier, elements)` | `elements.add_elements(dim, hier, [Element(...)])` | Append to existing dimension |
| `delete_elements(dim, hier, element_names)` | `elements.delete_elements(dim, hier, names)` | TM1 v11.4+; fallback to per-element delete |
| `update_hierarchy(dim, hier, add_edges, remove_edges)` | `elements.add_edges()` + `elements.delete_edges()` | Accept two lists of edge dicts |
| `create_element_attribute(dim, hier, attr_name, attr_type)` | `elements.create_element_attribute(dim, hier, ElementAttribute(...))` | Add new attribute column |
| `write_element_attributes(dim, hier, attribute_values)` | `elements.update_or_create` per element | attribute_values: `[{"element": "X", "attr": "Alias", "value": "Y"}]` |

**Imports to add:** `from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute`

**Verify:** `python -m py_compile tm1_mcp_server/tm1_connector.py`

### A2. MCP tools — `tm1_mcp_server/tm1_mcp_tool.py`

Add 7 `@mcp.tool` functions. Insert before the `# Entry point` section (before line 922):

| Tool | Annotation | Maps to |
|------|-----------|---------|
| `create_dimension` | — | `mgr.create_dimension(...)` |
| `delete_dimension` | DESTRUCTIVE | `mgr.delete_dimension(...)` |
| `add_elements` | — | `mgr.add_elements(...)` |
| `delete_elements` | DESTRUCTIVE | `mgr.delete_elements(...)` |
| `update_hierarchy` | — | `mgr.update_hierarchy(...)` |
| `create_element_attribute` | — | `mgr.create_element_attribute(...)` |
| `write_element_attributes` | — | `mgr.write_element_attributes(...)` |

All use `_coerce_str_to_list()` for `elements` / `edges` / `attribute_values` parameters.

**Verify:** `python -m py_compile tm1_mcp_server/tm1_mcp_tool.py`

### A3. Tests — `tests/test_dimension_write.py`

Test fixture: create a test dimension with prefix `Claude_Test_`, delete in teardown.

| Test | What it verifies |
|------|-----------------|
| `test_create_dimension_simple` | Create with N elements only, verify via `get_dimension_info` |
| `test_create_dimension_with_hierarchy` | Create with C/N elements + edges, verify element counts and parents |
| `test_delete_dimension` | Create then delete, verify dimension absent |
| `test_add_elements` | Create empty, add elements after, verify count increased |
| `test_delete_elements` | Create with elements, delete some, verify remaining |
| `test_update_hierarchy_add_edges` | Add consolidation edges, verify via `get_parents` |
| `test_update_hierarchy_remove_edges` | Remove edges, verify parent gone |
| `test_create_element_attribute` | Add attribute, verify via `get_element_attributes` |
| `test_write_element_attributes` | Write attribute values, read back and verify |
| `test_create_dimension_duplicate` | Error case: create same dimension twice |

**Verify:** `python -m pytest tests/test_dimension_write.py -v --tb=short`

**Checkpoint A:** All dimension write tools pass tests. Move to B + C in parallel.

---

## Phase B: Subset Write Tools

**Depends on:** Phase A (needs dimensions to create subsets in)

### B1. Connector methods

Add 3 methods to `TM1Manager`:

| Method | TM1py API |
|--------|-----------|
| `create_subset(dim, hier, subset_name, elements, expression)` | `subsets.create(Subset(...))` — static if elements given, dynamic if expression given |
| `update_subset(dim, hier, subset_name, elements, expression)` | `subsets.update(Subset(...))` |
| `delete_subset(dim, hier, subset_name)` | `subsets.delete(name, dim, hier)` |

**Import:** `from TM1py.Objects import Subset`

### B2. MCP tools

| Tool | Annotation |
|------|-----------|
| `create_subset` | — |
| `update_subset` | — |
| `delete_subset` | DESTRUCTIVE |

### B3. Tests — `tests/test_subset_write.py`

| Test | What it verifies |
|------|-----------------|
| `test_create_subset_static` | Create static subset with element list, verify via `get_subset` |
| `test_create_subset_dynamic` | Create MDX subset with expression, verify type = dynamic |
| `test_update_subset_elements` | Change static subset membership, verify |
| `test_delete_subset` | Create then delete, verify absent |
| `test_create_subset_missing_dimension` | Error case |

**Checkpoint B:** Subset tools pass. Can proceed independently.

---

## Phase C: Cube Write Tools

**Depends on:** Phase A (cubes need dimensions)

### C1. Connector methods

Add 2 methods:

| Method | TM1py API |
|--------|-----------|
| `create_cube(name, dimensions)` | `cubes.create(Cube(name, dims))` |
| `delete_cube(name)` | `cubes.delete(name)` |

**Import:** `from TM1py.Objects import Cube`

### C2. MCP tools

| Tool | Annotation |
|------|-----------|
| `create_cube` | — |
| `delete_cube` | DESTRUCTIVE |

### C3. Tests — `tests/test_cube_write.py`

Uses test dimensions from Phase A.

| Test | What it verifies |
|------|-----------------|
| `test_create_cube` | Create cube with 3 dims, verify via `get_cube` (dimension order) |
| `test_delete_cube` | Create then delete, verify absent |
| `test_create_cube_wrong_dimension` | Error case: non-existent dimension |

**Checkpoint C:** Cube tools pass. Proceed to D + E in parallel.

---

## Phase D: View Write Tools

**Depends on:** Phase C (views belong to cubes)

### D1. Connector methods

Add 2 methods:

| Method | TM1py API |
|--------|-----------|
| `create_view(cube, view_name, mdx)` | `views.create(MDXView(cube, name, mdx))` |
| `delete_view(cube, view_name, private)` | `views.delete(cube, name, private)` |

**Import:** `from TM1py.Objects import MDXView`

### D2. MCP tools

| Tool | Annotation |
|------|-----------|
| `create_view` | — |
| `delete_view` | DESTRUCTIVE |

### D3. Tests — `tests/test_view_write.py`

| Test | What it verifies |
|------|-----------------|
| `test_create_mdx_view` | Create view with MDX, verify via `get_view_structure` |
| `test_delete_view` | Create then delete, verify absent |
| `test_create_view_missing_cube` | Error case |

**Checkpoint D:** View tools pass.

---

## Phase E: Data Write Tools

**Depends on:** Phase C (data lives in cubes)

### E1. Connector methods

Add 4 methods:

| Method | TM1py API | Notes |
|--------|-----------|-------|
| `write_cell(cube, elements, value)` | `cells.write_value(value, cube, tuple)` | Single cell |
| `write_bulk(cube, cellset, dimensions)` | `cells.write(cube, dict, use_blob=True)` | Dict format: `{("e1","e2","e3"): value}` |
| `write_file(cube, file_path, dimensions)` | `cells.write_dataframe(cube, df, ...)` | Read CSV/Excel with pandas, write via dataframe |
| `clear_cube(cube, filter_mdx)` | `cells.clear(cube, **mdx_filters)` or `cells.clear_with_mdx(cube, mdx)` | Clear all or slice |

**Import:** `import pandas as pd`

**Key detail:** `write_file` needs to:
1. Detect file type from extension (.csv, .xlsx, .xls)
2. Read into DataFrame
3. Optionally accept `dimensions` parameter to map columns to cube dimensions
4. Call `cells.write_dataframe(cube, df, dimensions=dimensions)`

### E2. MCP tools

| Tool | Annotation |
|------|-----------|
| `write_cell` | — |
| `write_bulk` | — |
| `write_file` | — |
| `clear_cube` | DESTRUCTIVE |

**Note:** `write_bulk` takes `cellset_as_json: str` parameter (JSON string of the cellset dict), uses `_coerce_str_to_list()` pattern but for dict. `write_file` takes a local file path.

### E3. Tests — `tests/test_data_write.py`

Requires a test cube (from Phase C) with test data.

| Test | What it verifies |
|------|-----------------|
| `test_write_cell` | Write single value, verify via `get_cell` |
| `test_write_bulk` | Write multiple cells, verify via `execute_mdx` |
| `test_write_file_csv` | Write from CSV file, verify via `execute_mdx` |
| `test_clear_cube` | Write data then clear, verify zero |
| `test_clear_cube_with_filter` | Clear slice only, verify other data intact |
| `test_write_cell_string` | Write string value, verify |
| `test_write_bulk_missing_cube` | Error case |

**Checkpoint E:** Data tools pass.

---

## Phase F: Verification Tools

**Depends on:** Phase A + C (verifies dims and cubes)

### F1. Connector methods

Add 2 methods:

| Method | Logic |
|--------|-------|
| `verify_dimension(dim, expected_elements, expected_attributes)` | Compare actual element count + types against expected. Return `{match, actual, expected, differences}` |
| `verify_cube(cube, expected_dimensions, check_has_data)` | Check dimension order, existence, optionally sample data presence |

### F2. MCP tools

| Tool | Annotation |
|------|-----------|
| `verify_dimension` | RO |
| `verify_cube` | RO |

### F3. Tests — `tests/test_verify.py`

| Test | What it verifies |
|------|-----------------|
| `test_verify_dimension_match` | Create dimension, verify with matching spec → passes |
| `test_verify_dimension_mismatch` | Verify with wrong element count → reports differences |
| `test_verify_dimension_missing_attribute` | Verify with expected attribute that doesn't exist → reports |
| `test_verify_cube_match` | Create cube, verify with matching dims → passes |
| `test_verify_cube_wrong_order` | Verify with swapped dims → reports mismatch |
| `test_verify_cube_missing` | Verify non-existent cube → reports missing |

**Checkpoint F:** Verify tools pass.

---

## Phase G: Skill & References

**Depends on:** All tools functional. Can draft references in parallel with E/F.

### G1. Skill directory structure

Create `.claude/skills/tm1-model-builder/`:

```
.claude/skills/tm1-model-builder/
  SKILL.md
  references/
    dimension-ops.md
    cube-ops.md
    data-ops.md
    mcp-tools-reference.md
    coding-conventions.md
  templates/
    dimension-spec.json
    cube-spec.json
```

### G2. SKILL.md (router)

Lean router (~120 lines) that:
1. Detects task type (dimension / cube / data / full build)
2. Routes to the appropriate reference doc
3. Defines the 5-phase workflow (Understand → Plan → Build → Verify → Hand off)
4. References `tm1-process-writer` for TI logic handoff

### G3. Reference docs

- `dimension-ops.md` — Patterns for building dimensions, hierarchy patterns (flat, balanced, ragged), subset patterns
- `cube-ops.md` — Cube creation patterns, view patterns, dimension ordering
- `data-ops.md` — Cell write patterns, bulk strategies, file-based loading
- `mcp-tools-reference.md` — Complete tool inventory (read + write) with usage examples
- `coding-conventions.md` — Naming, annotation, error handling conventions

### G4. Templates

- `dimension-spec.json` — JSON template for describing a dimension build spec
- `cube-spec.json` — JSON template for describing a cube creation spec

**Checkpoint G:** SKILL.md loads without error, Claude Code correctly routes to references based on task type.

---

## Summary: Task Count

| Phase | Connector methods | MCP tools | Tests | New files |
|-------|-------------------|-----------|-------|-----------|
| A: Dimension | 7 | 7 | 10 | 1 (test file) |
| B: Subset | 3 | 3 | 5 | 1 |
| C: Cube | 2 | 2 | 3 | 1 |
| D: View | 2 | 2 | 3 | 1 |
| E: Data | 4 | 4 | 7 | 1 + test CSV |
| F: Verify | 2 | 2 | 6 | 1 |
| G: Skill | 0 | 0 | 0 | 8 |
| **Total** | **20** | **20** | **34** | **14** |

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| TM1py `delete_elements` requires v11.4+ | Fallback: loop `elements.delete()` per element. Detect version in connector. |
| `write_file` needs openpyxl for .xlsx | Check if openpyxl is installed; if not, support CSV only and document the limitation. |
| `clear_cube` API varies by TM1 version | Try `cells.clear()` first (v11.7+), fallback to `cells.clear_with_mdx()`. |
| Context window pressure from 20 new tools | Each MCP tool description is ~200 tokens. 20 tools = ~4k tokens. Acceptable. |
| Test dimensions/cubes polluting dev server | Use `Claude_Test_` prefix, cleanup in teardown, add a cleanup utility that removes all `Claude_Test_*` objects. |
