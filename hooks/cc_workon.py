"""
PreToolUse hook (matcher: Bash): cc-workon session registration.

Intercepts Bash commands containing "cc-workon <path>" and registers
the session's active project in sessions.json.

All other Bash commands pass through (exit 0).
"""

import sys
import json
import os
import re
import traceback

from session_store import (
    load_sessions,
    save_sessions,
    cleanup_stale_sessions,
    acknowledge,
    block,
    PROJECT_ROOT,
)


# ── Session registration ──────────────────────────────────────────────


def register_session(session_id, project_path, cwd):
    """Register or update a session's active project."""
    abs_path = os.path.normpath(os.path.join(cwd, project_path))
    # Prevent path traversal outside project root
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
        "updated_at": __import__("time").time(),
    }
    save_sessions(data)
    acknowledge(
        f"CC-WORKON: Session registered -> {project_path}\n"
        "You can now use MCP write tools for this project "
        "(subject to spec review gate)."
    )


# ── cc-workon command handling ────────────────────────────────────────


def handle_cc_workon(command, cwd, session_id):
    """Parse and process cc-workon command from Bash tool."""
    match = re.search(r'cc-workon\s+([^\s\'"]+)', command)
    if not match:
        block(
            "CC-WORKON: Invalid syntax. Usage: : cc-workon <project_path>\n"
            "Example: : cc-workon models/Sales_Planning"
        )
    project_path = match.group(1).strip("'\"")
    register_session(session_id, project_path, cwd)


# ── Main entry point ──────────────────────────────────────────────────


def main():
    try:
        raw_input = sys.stdin.read()
        try:
            input_data = json.loads(raw_input)
        except (json.JSONDecodeError, EOFError):
            print(
                "CC-WORKON: Failed to parse hook input.\n"
                f"Raw stdin (first 500 chars): {raw_input[:500]!r}",
                file=sys.stderr,
            )
            sys.exit(2)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", os.getcwd())
        session_id = input_data.get("session_id", "")

        # Only handle Bash tool
        if tool_name != "Bash":
            sys.exit(0)

        command = tool_input.get("command", "")
        if "cc-workon" not in command:
            sys.exit(0)  # Not a cc-workon command, allow

        handle_cc_workon(command, cwd, session_id)

    except SystemExit:
        raise
    except Exception as e:
        print(
            f"CC-WORKON: Hook error — blocking for safety.\n"
            f"Exception: {type(e).__name__}: {e}\n"
            f"Traceback:\n{traceback.format_exc()}",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
