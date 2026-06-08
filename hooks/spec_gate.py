"""
PreToolUse hook (matcher: mcp__tm1__*): spec review gate.

Verifies the session has a registered project with valid specs + .reviewed
status before allowing MCP TM1 write/destructive tools.

Read-only TM1 tools pass through immediately (exit 0).
Unrecognized TM1 tools are denied (exit 2).
"""

import sys
import json
import os
import glob
import traceback

from session_store import (
    get_active_project,
    block,
)


# ── Tool classification ───────────────────────────────────────────────

READONLY_TOOLS = {
    "mcp__tm1__list_instances", "mcp__tm1__list_cubes",
    "mcp__tm1__list_dimensions", "mcp__tm1__list_processes",
    "mcp__tm1__list_subsets", "mcp__tm1__list_views",
    "mcp__tm1__get_cube", "mcp__tm1__get_cube_rules",
    "mcp__tm1__get_dimension_info", "mcp__tm1__get_element_attributes",
    "mcp__tm1__get_leaf_elements", "mcp__tm1__get_parents",
    "mcp__tm1__get_process", "mcp__tm1__get_process_error_log",
    "mcp__tm1__get_process_template", "mcp__tm1__get_subset",
    "mcp__tm1__get_view_structure", "mcp__tm1__execute_mdx",
    "mcp__tm1__execute_view_query", "mcp__tm1__expand_element",
    "mcp__tm1__find_cubes_by_dimension", "mcp__tm1__get_cell",
    "mcp__tm1__verify_cube", "mcp__tm1__verify_dimension",
    "mcp__tm1__search_processes", "mcp__tm1__compile_process",
}

GATED_TOOLS = {
    # Model building
    "mcp__tm1__create_dimension", "mcp__tm1__create_dimension_file",
    "mcp__tm1__add_elements", "mcp__tm1__add_elements_file",
    "mcp__tm1__create_cube",
    "mcp__tm1__create_subset", "mcp__tm1__update_subset",
    "mcp__tm1__create_view",
    "mcp__tm1__write_cell", "mcp__tm1__write_bulk", "mcp__tm1__write_file",
    "mcp__tm1__write_element_attributes", "mcp__tm1__write_element_attributes_file",
    "mcp__tm1__update_hierarchy", "mcp__tm1__update_hierarchy_file",
    "mcp__tm1__create_element_attribute",
    # Process
    "mcp__tm1__create_process", "mcp__tm1__update_process",
    "mcp__tm1__execute_process",
    # Destructive
    "mcp__tm1__delete_cube", "mcp__tm1__delete_dimension",
    "mcp__tm1__delete_elements", "mcp__tm1__delete_process",
    "mcp__tm1__delete_subset", "mcp__tm1__delete_view",
    "mcp__tm1__clear_cube",
}

# ── Spec file patterns ────────────────────────────────────────────────

MODEL_SPEC_PATTERNS = ["*_dimension-spec.json", "*_cube-spec.json"]
PROCESS_SPEC_PATTERNS = ["*_prolog.ti", "*_data.ti"]


# ── Spec gate logic ───────────────────────────────────────────────────


def has_spec_files(project_dir):
    """Check if project directory contains spec/code files."""
    is_process = "processes" in project_dir.replace("\\", "/")
    patterns = PROCESS_SPEC_PATTERNS if is_process else MODEL_SPEC_PATTERNS
    for pattern in patterns:
        if glob.glob(os.path.join(project_dir, pattern)):
            return True
    return False


def is_reviewed_valid(project_dir):
    """Check .reviewed exists and specs haven't been modified after it."""
    reviewed_path = os.path.join(project_dir, ".reviewed")
    if not os.path.exists(reviewed_path):
        return False, "No .reviewed file found"

    reviewed_mtime = os.path.getmtime(reviewed_path)
    for f in os.listdir(project_dir):
        if f.startswith("."):
            continue
        if f.endswith(("-spec.json", ".ti", ".json")):
            fpath = os.path.join(project_dir, f)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) > reviewed_mtime:
                return (
                    False,
                    f".reviewed expired ('{f}' modified after review)",
                )
    return True, ""


def check_spec_gate(project_dir):
    """Run the spec gate decision tree on the project directory."""
    project_name = os.path.basename(project_dir)

    # ── Bypass check ──
    if os.path.exists(os.path.join(project_dir, ".spec_bypass")):
        return  # ALLOW — improvising mode

    # ── Spec files check ──
    if not has_spec_files(project_dir):
        block(
            f"SPEC REVIEW GATE: No spec files found in {project_name}/.\n"
            "Please do one of the following:\n"
            "  1. Invoke the appropriate skill (tm1-model-builder or "
            "tm1-process-writer) to generate spec/code files\n"
            "  2. If this is an improvising/temp operation, ask the user "
            "to confirm, then create a .spec_bypass file in the project directory"
        )

    # ── Reviewed check ──
    valid, reason = is_reviewed_valid(project_dir)
    if not valid:
        block(
            f"SPEC REVIEW GATE: {reason} in {project_name}/.\n"
            "You MUST complete these steps before using MCP write tools:\n"
            "  1. Show ALL spec/code files to the user using AskUserQuestion\n"
            "  2. Wait for explicit user approval\n"
            f"  3. Create .reviewed marker: touch {project_name}/.reviewed\n"
            "Spec files modified after review require re-approval."
        )

    # All checks passed -> ALLOW (fall through to exit 0)


# ── Main entry point ──────────────────────────────────────────────────


def main():
    try:
        raw_input = sys.stdin.read()
        try:
            input_data = json.loads(raw_input)
        except (json.JSONDecodeError, EOFError):
            print(
                f"SPEC REVIEW GATE: Failed to parse hook input.\n"
                f"Raw stdin (first 500 chars): {raw_input[:500]!r}",
                file=sys.stderr,
            )
            sys.exit(2)

        tool_name = input_data.get("tool_name", "")
        cwd = input_data.get("cwd", os.getcwd())
        session_id = input_data.get("session_id", "")

        # ── Fast path: read-only tools ──
        if tool_name in READONLY_TOOLS:
            sys.exit(0)

        # ── Spec gate: gated tools ──
        if tool_name in GATED_TOOLS:
            project_dir = get_active_project(session_id, cwd)

            if not project_dir:
                block(
                    "SPEC REVIEW GATE: No active project registered for this session.\n"
                    "Before using any TM1 MCP write tools, you MUST run:\n"
                    "  : cc-workon <project_path>\n"
                    "Example: : cc-workon models/Sales_Planning\n"
                    "This registers the current session's working project."
                )

            check_spec_gate(project_dir)
            # If we reach here, all checks passed -> ALLOW
            sys.exit(0)

        # ── Default deny for unrecognized TM1 tools ──
        if tool_name.startswith("mcp__tm1__"):
            print(
                f"SPEC REVIEW GATE: Unrecognized TM1 tool '{tool_name}' is not classified.",
                file=sys.stderr,
            )
            sys.exit(2)

        # ── Default: allow (should not reach here with current matcher) ──
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        print(
            f"SPEC REVIEW GATE: Hook error — blocking for safety.\n"
            f"Exception: {type(e).__name__}: {e}\n"
            f"Traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
