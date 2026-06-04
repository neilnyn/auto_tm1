"""
PreToolUse hook: Spec Review Gate for TM1 MCP write tools.

Enforces the spec-driven workflow for TM1 model development.

Gate logic:
  - models/ doesn't exist         → WARN: guide to set up spec directory
  - No spec files in models/       → WARN: guide to create specs via tm1-model-builder
  - Spec files exist, reviewed     → ALLOW
  - Spec files exist, unreviewed   → BLOCK (exit 2)
"""

import sys
import json
import os
import glob


GATED_TOOLS = {
    "mcp__tm1__create_dimension_file",
    "mcp__tm1__create_dimension",
    "mcp__tm1__create_cube",
    "mcp__tm1__create_subset",
    "mcp__tm1__create_view",
    "mcp__tm1__write_bulk",
    "mcp__tm1__write_cell",
    "mcp__tm1__write_file",
}

SPEC_PATTERNS = [
    "**/*_dimension-spec.json",
    "**/*_cube-spec.json",
]


def is_model_dir_reviewed(model_dir):
    reviewed_path = os.path.join(model_dir, ".reviewed")
    if not os.path.exists(reviewed_path):
        return False
    reviewed_mtime = os.path.getmtime(reviewed_path)
    for f in os.listdir(model_dir):
        if f.endswith("-spec.json"):
            if os.path.getmtime(os.path.join(model_dir, f)) > reviewed_mtime:
                return False
    return True


def warn(message):
    """Exit 0 with additionalContext injected into LLM context."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def block(message):
    """Exit 2 to block the tool call, message shown to LLM."""
    print(message, file=sys.stderr)
    sys.exit(2)


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name not in GATED_TOOLS:
        sys.exit(0)

    cwd = input_data.get("cwd", os.getcwd())
    models_dir = os.path.join(cwd, "models")

    if not os.path.isdir(models_dir):
        warn(
            "SPEC WORKFLOW NOTICE: The models/ directory does not exist. "
            "This project uses a spec-driven workflow for TM1 development. "
            "Please invoke the tm1-model-builder skill to set up the proper "
            "directory structure (models/<model_summary>/*_dimension-spec.json, "
            "*_cube-spec.json) before using MCP write tools."
        )

    spec_files = []
    for pattern in SPEC_PATTERNS:
        spec_files.extend(glob.glob(os.path.join(models_dir, pattern), recursive=True))

    if not spec_files:
        warn(
            "SPEC WORKFLOW NOTICE: No spec files found in models/. "
            "This project requires dimension/cube spec files as the basis for "
            "all MCP write operations. Please invoke the tm1-model-builder skill "
            "to generate spec files (models/<model_summary>/*_dimension-spec.json, "
            "*_cube-spec.json) and get user review before proceeding."
        )

    model_dirs = set(os.path.dirname(f) for f in spec_files)
    unreviewed = [d for d in model_dirs if not is_model_dir_reviewed(d)]

    if not unreviewed:
        sys.exit(0)

    names = [os.path.relpath(d, models_dir) for d in unreviewed]
    block(
        f"SPEC REVIEW GATE: Spec files in models/{', models/'.join(names)} "
        "have NOT been user-reviewed. "
        "You MUST: (1) Show ALL spec file contents to the user using AskUserQuestion, "
        "(2) Wait for explicit user approval, "
        f"(3) Create .reviewed marker in: {', '.join(names)}. "
        "Only then can MCP write tools proceed."
    )


if __name__ == "__main__":
    main()
