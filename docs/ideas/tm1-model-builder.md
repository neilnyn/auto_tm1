# TM1 Model Builder

## Problem Statement

How might we expand Auto_TM1 from a TI-process writer into a full AI-powered TM1 model construction platform, so that Claude Code can build, populate, and verify complete TM1 models end-to-end?

## Recommended Direction

Create a single unified skill `tm1-model-builder` that covers dimension, cube, view, subset, and data operations. Instead of three separate skills, one skill acts as an orchestrator with domain-specific reference docs (`dimension-ops.md`, `cube-ops.md`, `data-ops.md`) serving as sub-routes. Claude Code's rules mechanism and reference doc structure handle the navigation — the SKILL.md itself stays lean as a router, detail lives in the references.

Alongside the skill, build out all write MCP tools in the existing `tm1_connector.py` / `tm1_mcp_tool.py` architecture. Add a verification/testing layer woven into the skill workflow so every build operation gets validated automatically — not as an optional step, but as part of the flow.

This gives TM1 developers a closed-loop platform: explore → build skeleton → create cubes → seed data → verify → write TI logic. The existing `tm1-process-writer` skill remains independent for pure TI development. Together, the two skills cover the full lifecycle.

## Key Assumptions to Validate

- [ ] Claude Code can effectively route to the right reference doc based on task context (build dimension vs create cube vs write data) — validate by building the dimension reference first and testing routing
- [ ] A lean router SKILL.md (under ~150 lines) is sufficient to guide behavior without becoming context noise — validate by writing it and measuring whether Claude Code loads unnecessary references
- [ ] Automatic verification steps don't slow down the workflow enough to annoy users — validate by timing the verify phase on a real build sequence
- [ ] TM1py's write APIs are stable and complete enough for the operations we need — validate by prototyping dimension CRUD first, since it's the foundation

## MVP Scope

### Layer 1: MCP Write Tools (`tm1_connector.py` + `tm1_mcp_tool.py`)

**Dimension operations:**
- create_dimension — create dimension with elements and hierarchy
- delete_dimension — delete a dimension (destructiveHint)
- add_elements — add N/S/C elements to a dimension
- delete_elements — remove elements from a dimension (destructiveHint)
- update_hierarchy — add/remove consolidation children, set weights
- create_attribute / update_attribute — manage element attributes
- create_subset / update_subset / delete_subset — subset CRUD (static + dynamic MDX)

**Cube & View operations:**
- create_cube — create cube with ordered dimensions
- delete_cube — delete a cube (destructiveHint)
- create_view — create view with axis layout (columns/rows/titles)
- delete_view — delete a view (destructiveHint)

**Data operations:**
- write_cell — write single cell value
- write_bulk — bulk write from record list
- clear_cube — zero out cube data (destructiveHint)

**Verification tools:**
- verify_dimension — check element counts, hierarchy integrity, attribute coverage
- verify_cube — check dimension order, rule status, data presence

### Layer 2: Skill (`tm1-model-builder`)

```
.claude/skills/tm1-model-builder/
  SKILL.md                          -- Router: phase definitions, routing logic
  references/
    dimension-ops.md                -- Dimension/subset patterns, conventions, examples
    cube-ops.md                     -- Cube/view patterns, conventions, examples
    data-ops.md                     -- Data read/write patterns, bulk operations guide
    mcp-tools-reference.md          -- Updated tool reference including new write tools
    coding-conventions.md           -- Shared conventions (naming, error handling, annotations)
  templates/
    dimension-spec.json             -- Template for dimension build specifications
    cube-spec.json                  -- Template for cube creation specifications
```

### Layer 3: Skill Workflow

1. **Understand** — User describes what to build (or provides a spec). Claude Code explores existing model with read-only tools.
2. **Plan** — Claude Code presents a build plan with verification criteria. User approves.
3. **Build** — Execute in order: dimensions → subsets → cubes → views → data. Each step includes automatic verification.
4. **Verify** — Run verification tools after each major phase. Surface discrepancies immediately.
5. **Hand off** — If TI logic is needed, hand off context to `tm1-process-writer` skill.

## Not Doing (and Why)

- **Security/ACL operations** — out of scope for this iteration; belongs in a future `tm1-admin` skill
- **Server administration** (config, transaction logs) — not part of the model builder story
- **Rule creation/management** — cube rules are tightly coupled to TI logic; keep in `tm1-process-writer` domain for now
- **Separate skills per domain** — one router skill beats three; the rules/reference mechanism handles sub-routing without installation overhead
- **Production safety gates** — all operations target dev environments; skip dry_run/approval ceremony for now
- **Automated test suite for MCP tools** — tests exist but coverage is light; expand test coverage as a follow-up, not a prerequisite

## Relationship to Existing Skill

`tm1-process-writer` remains independent and unchanged. The two skills cooperate:

```
tm1-model-builder          tm1-process-writer
       │                          │
  Build structure          Implement logic
  (dims, cubes, data)      (TI processes)
       │                          │
       └────── shared MCP tools ──┘
```

Claude Code can invoke either independently, or chain them: model-builder first, then process-writer for business logic.

## Decisions

- `verify_dimension` / `verify_cube` are MCP tools — callable from any context, usable outside the skill workflow for ad-hoc validation.
- All new MCP tools follow **verb_noun** convention (`create_dimension`, `write_cell`, `clear_cube`). Existing tools (`find_cubes_by_dimension` etc.) are grandfathered in; new tools normalize from here forward.
- Bulk data write accepts **file paths** (CSV/Excel). TM1 projects deal with large datasets where in-memory records are impractical. File-based input also lets users hand Claude Code a local export and say "load this."
