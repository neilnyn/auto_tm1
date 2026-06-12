"""
Stop hook: clear session binding after every turn.

Removes the current session's entry from sessions.json when the turn ends.
This ensures every new turn starts with a clean slate — a fresh cc-workon
is required before any MCP write operations.

Design: fail-open (exit 0 on all errors). Stop fires at the end of a turn
and must not block it. A failed cleanup is low-risk — stale entries expire
after 24 hours via cleanup_stale_sessions().
"""

import sys
import json
import traceback

from session_store import (
    load_sessions,
    save_sessions,
    cleanup_stale_sessions,
    parser_hook_input,
)


def main():
    try:
        raw_input = sys.stdin.read()
        try:
            input_data = parser_hook_input(raw_input)
        except (json.JSONDecodeError, EOFError):
            # Fail silently on Stop — don't block the turn ending
            sys.exit(0)

        session_id = input_data.get("session_id", "")
        if not session_id:
            sys.exit(0)

        data = load_sessions()
        if session_id in data:
            del data[session_id]
        cleanup_stale_sessions(data)
        save_sessions(data)
        sys.exit(0)

    except SystemExit:
        raise
    except Exception:
        # Fail silently on Stop — don't block the turn ending
        sys.exit(0)


if __name__ == "__main__":
    main()
