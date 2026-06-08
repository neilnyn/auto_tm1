"""
Shared module: sessions.json CRUD + hook output helpers.

Imported by cc_workon.py, spec_gate.py, session_cleanup.py.
Not intended to be run directly.
"""

import sys
import json
import os
import time

# ── Constants ─────────────────────────────────────────────────────────

SESSION_EXPIRY_SECONDS = 86400  # 24 hours

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_FILE = os.path.join(_HOOKS_DIR, "sessions.json")
PROJECT_ROOT = os.path.dirname(_HOOKS_DIR)


# ── Output helpers ────────────────────────────────────────────────────


def acknowledge(message):
    """Exit 0 with additionalContext — feedback for PreToolUse hooks."""
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


# ── sessions.json management ──────────────────────────────────────────


def load_sessions():
    """Load sessions.json, return dict. Empty dict on missing/corrupt file."""
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_sessions(data):
    """Write sessions.json atomically via tmp + os.replace."""
    tmp = SESSIONS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.replace(tmp, SESSIONS_FILE)
    except OSError:
        os.remove(SESSIONS_FILE)
        os.rename(tmp, SESSIONS_FILE)


def cleanup_stale_sessions(data):
    """Remove entries older than SESSION_EXPIRY_SECONDS. Mutates in place."""
    cutoff = time.time() - SESSION_EXPIRY_SECONDS
    stale = [sid for sid, info in data.items()
             if info.get("updated_at", 0) < cutoff]
    for sid in stale:
        del data[sid]
    return bool(stale)


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
