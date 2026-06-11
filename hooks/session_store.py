"""
Shared module: sessions.json CRUD + hook output helpers.

Imported by cc_workon.py, spec_gate.py, session_cleanup.py.
Not intended to be run directly.
"""

import sys
import json
import os
import time

# —— JSON repair for Windows paths ————————————————————————————————————————


def _is_valid_unicode_escape(raw: str, i: int) -> bool:
    """Check if raw[i:] is a valid \\uXXXX sequence (4 hex digits after \\u)."""
    if i + 5 >= len(raw):
        return False
    return raw[i + 1] == "u" and all(c in "0123456789abcdefABCDEF" for c in raw[i + 2 : i + 6])


def parser_hook_input(raw: str) -> dict:
    r"""Parse Claude Code hook stdin JSON with fallback repair for Windows path escaping bugs.

    **Background problem:**
    Some Claude Code forks/wrappers (e.g. CodeFuse on Windows) produce malformed JSON
    via stdin where backslashes in Windows paths are inconsistently escaped. For example,
    the same path may contain both correctly escaped ``\\`` and unescaped ``\.``,
    ``\P``, etc., which are not valid JSON escape sequences and cause ``json.loads()``
    to fail. This was first observed with a path like::

        "C:\\Users\\X\.codefuse\\engine\\..."

    where ``\.codefuse`` has a single backslash (``\.`` is invalid in JSON).

    **Repair strategy:**
    1. Try standard ``json.loads()`` first (fast path — works for official Claude Code).
    2. On failure, walk the raw string character by character, tracking JSON string
       boundaries (``"``). Inside strings, when encountering ``\`` followed by a char:
       - If it's a valid JSON escape (``" \ / b f n r t uXXXX``), keep as-is.
       - Otherwise (e.g. ``\.``, ``\P``, ``\U``), double the backslash to ``\\``.
    3. If repair also fails, raise ``json.JSONDecodeError`` so the caller can decide
       (e.g. fail-open vs block).

    **Why \u is special:**
    All JSON escapes except ``\uXXXX`` are exactly 2 characters (``\n``, ``\t``, etc.).
    ``\u`` requires 4 additional hex digits. If a Windows path contains ``\users``,
    blindly keeping ``\u`` as valid would produce an invalid ``\us`` escape.
    Hence ``\u`` is checked separately via ``_is_valid_unicode_escape()``.

    **Usage example (in a PreToolUse hook)::**

        from session_store import parser_hook_input

        def main():
            raw = sys.stdin.read()
            try:
                input_data = parser_hook_input(raw)
            except json.JSONDecodeError:
                # Fail open: can't enforce gate without valid input
                print("HOOK: stdin JSON unparseable, failing open", file=sys.stderr)
                sys.exit(0)
            tool_name = input_data.get("tool_name", "")

    Args:
        raw: The raw JSON string read from ``sys.stdin.read()``.

    Returns:
        Parsed dict from the JSON input (or repaired JSON).

    Raises:
        json.JSONDecodeError: If neither standard parsing nor repair succeeds.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # valid JSON escape characters after backslash: " \ / b f n r t
        # note: 'u' is handled separately via _is_valid_unicode_escape()
        simple_valid_escapes = set('\"\\/bfnrt')
        repaired = []
        in_string = False
        i = 0
        while i < len(raw):
            ch = raw[i]
            if in_string:
                if ch == '\\' and i + 1 < len(raw):
                    next_ch = raw[i + 1]
                    # \uXXXX requires 4 hex digits — check separately
                    if next_ch == 'u':
                        if _is_valid_unicode_escape(raw, i):
                            repaired.append(raw[i:i + 6])
                            i += 6
                            continue
                        else:
                            repaired.append('\\\\')
                            repaired.append(next_ch)
                            i += 2
                            continue
                    elif next_ch in simple_valid_escapes:
                        repaired.append(ch)
                        repaired.append(next_ch)
                        i += 2
                        continue
                    else:
                        # Invalid escape like \. \P \U — double the backslash
                        repaired.append('\\\\')
                        repaired.append(next_ch)
                        i += 2
                        continue
                elif ch == '"':
                    in_string = False
                    repaired.append(ch)
                    i += 1
                    continue
                else:
                    repaired.append(ch)
                    i += 1
                    continue
            else:
                if ch == '"':
                    in_string = True
                repaired.append(ch)
                i += 1

        repaired_str = ''.join(repaired)
        # Let json.JSONDecodeError propagate so caller can decide fail-open vs block
        return json.loads(repaired_str)


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


def get_active_project(session_id):
    """Get absolute path of active project for a session. None if not set.

    The stored ``project`` is normalized relative to ``PROJECT_ROOT`` at
    registration time (see cc_workon.register_session), so resolution uses
    the stable PROJECT_ROOT rather than the hook's transient cwd. Reads no
    longer depend on the cwd supplied via stdin.
    """
    data = load_sessions()
    cleaned = cleanup_stale_sessions(data)
    if cleaned:
        save_sessions(data)

    info = data.get(session_id)
    if not info:
        return None
    return os.path.normpath(os.path.join(PROJECT_ROOT, info["project"]))
