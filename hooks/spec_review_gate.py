"""
PreToolUse hook: Spec Review Gate + cc-workon session tracker.

Two responsibilities:
  1. cc-workon: intercept Bash commands containing "cc-workon <path>",
     register the session's active project in hooks/sessions.json.
  2. Spec Gate: for MCP TM1 write/destructive tools, verify the session
     has a registered project with valid specs + reviewed status.

sessions.json format:
  {
    "session-abc123": {"project": "models/Sales_Planning", "updated_at": 1717500000},
    "session-def456": {"project": "processes/Load_Sales", "updated_at": 1717500100}
  }

Gate decision tree (only for write/destructive MCP tools):
  - No session registered           -> BLOCK  "Run cc-workon first"
  - .spec_bypass exists             -> ALLOW  (improvising pass)
  - No spec files in project dir    -> BLOCK  "Create specs or confirm improvising"
  - .reviewed valid (exists, fresh) -> ALLOW  (only green path)
  - .reviewed missing or expired    -> BLOCK  "Review specs and create .reviewed"

Read-only MCP tools are never gated.
"""

import sys
import json
import os
import time
import glob
import re
import traceback

# ── Tool classification ──────────────────────────────────────────────

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

# ── Spec file patterns ───────────────────────────────────────────────

MODEL_SPEC_PATTERNS = ["*_dimension-spec.json", "*_cube-spec.json"]
PROCESS_SPEC_PATTERNS = ["*_prolog.ti", "*_data.ti"]

# ── Constants ────────────────────────────────────────────────────────

SESSION_EXPIRY_SECONDS = 86400  # 24 hours
SESSIONS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sessions.json"
)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Output helpers ───────────────────────────────────────────────────


def acknowledge(message):
    """Exit 0 with additionalContext — cc-workon feedback or info."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def block(message):
    """Exit 2 — tool is blocked, stderr shown to LLM."""
    print(message, file=sys.stderr)
    sys.exit(2)


# ── sessions.json management ─────────────────────────────────────────


def load_sessions():
    """Load sessions.json, return dict."""
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_sessions(data):
    """Write sessions.json atomically."""
    tmp = SESSIONS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.replace(tmp, SESSIONS_FILE)
    except OSError:
        os.remove(SESSIONS_FILE)
        os.rename(tmp, SESSIONS_FILE)


def cleanup_stale_sessions(data):
    """Remove entries older than SESSION_EXPIRY_SECONDS. Returns True if any removed."""
    cutoff = time.time() - SESSION_EXPIRY_SECONDS
    stale = [sid for sid, info in data.items()
             if info.get("updated_at", 0) < cutoff]
    for sid in stale:
        del data[sid]
    return bool(stale)


def register_session(session_id, project_path, cwd):
    """Register or update a session's active project."""
    abs_path = os.path.normpath(os.path.join(cwd, project_path))
    # Critical #2: prevent path traversal outside project root
    if not abs_path.startswith(PROJECT_ROOT + os.sep):
        block(
            f"CC-WORKON ERROR: Path must be within the project repository: {project_path}\n"
            "Paths outside the project root are not allowed."
        )
    if not os.path.isdir(abs_path):
        block(
            f"CC-WORKON ERROR: Directory does not exist: {project_path}\n"
            "Please ensure the path is correct before proceeding."
        )

    data = load_sessions()
    cleanup_stale_sessions(data)
    data[session_id] = {
        "project": project_path.replace("\\", "/"),
        "updated_at": time.time(),
    }
    save_sessions(data)
    acknowledge(
        f"CC-WORKON: Session registered -> {project_path}\n"
        "You can now use MCP write tools for this project "
        "(subject to spec review gate)."
    )


def get_active_project(session_id, cwd):
    """Get absolute path of active project for a session. None if not set."""
    data = load_sessions()
    cleaned = cleanup_stale_sessions(data)
    if cleaned:
        save_sessions(data)

    info = data.get(session_id)
    if not info:
        return None
    return os.path.normpath(os.path.join(cwd, info["project"]))


# ── cc-workon command handling ───────────────────────────────────────


def handle_cc_workon(command, cwd, session_id):
    """Parse and process cc-workon command from Bash tool."""
    match = re.search(r'cc-workon\s+(\S+)', command)
    if not match:
        block(
            "CC-WORKON: Invalid syntax. Usage: : cc-workon <project_path>\n"
            "Example: : cc-workon models/Sales_Planning"
        )
    project_path = match.group(1)
    register_session(session_id, project_path, cwd)


# ── Spec gate logic ──────────────────────────────────────────────────


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


# ── Main entry point ─────────────────────────────────────────────────


def main():
    try:
        raw_input = sys.stdin.read()
        try:
            input_data = json.loads(raw_input)
        except (json.JSONDecodeError, EOFError):
            # Critical #3: fail closed on malformed input, include raw stdin for diagnosis
            print(
                f"SPEC REVIEW GATE: Failed to parse hook input.\n"
                f"Raw stdin (first 500 chars): {raw_input[:500]!r}",
                file=sys.stderr,
            )
            sys.exit(2)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", os.getcwd())
        session_id = input_data.get("session_id", "")

        # ── Fast path: read-only tools ──
        if tool_name in READONLY_TOOLS:
            sys.exit(0)

        # ── Handle cc-workon (Bash tool) ──
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if "cc-workon" not in command:
                sys.exit(0)  # Not a cc-workon command, allow
            handle_cc_workon(command, cwd, session_id)
            # handle_cc_workon always exits (acknowledge or block)

        # ── Spec gate: MCP TM1 write/destructive tools ──
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

        # ── Medium #9: default deny for unrecognized TM1 tools ──
        if tool_name.startswith("mcp__tm1__"):
            print(
                f"SPEC REVIEW GATE: Unrecognized TM1 tool '{tool_name}' is not classified.",
                file=sys.stderr,
            )
            sys.exit(2)

        # ── Default: allow ──
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        # Critical #1: fail closed on any unhandled error, include traceback for diagnosis
        print(
            f"SPEC REVIEW GATE: Hook error — blocking for safety.\n"
            f"Exception: {type(e).__name__}: {e}\n"
            f"Traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
