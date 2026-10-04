"""Credential masking for every byte devin-switch can print.

Two layers of defence:

1. *file level* — files whose name says they carry credentials
   (``credentials.toml``, ``.env*``, ``*.pem``/``*.key``/``*.p12``/``*.pfx``,
   stems containing ``credential``/``secret``/``token``) never have their
   contents diffed or shown at all. ``credentials.toml`` is stronger still:
   it is never managed — skipped in profiles, never read, never written.
2. *value level* — inside printable files, values under key names that look
   sensitive (``token``/``secret``/``password``/``api_key``/``auth``…) and
   strings that look like tokens (long alnum blobs, JWTs, ``sk-``/``ghp_``/
   ``xox``/… prefixed secrets) render as ``<redacted>``.
"""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

REDACTED = "<redacted>"

# --- file names -----------------------------------------------------------

NEVER_TOUCH_NAMES = frozenset({"credentials.toml"})

_CREDENTIAL_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "credentials.toml",
        "secrets.json",
        "secrets.toml",
        "secrets.yaml",
        "secrets.yml",
        ".netrc",
        "id_rsa",
        "id_ed25519",
    }
)
_CREDENTIAL_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".jks")
_CREDENTIAL_STEM_WORDS = ("credential", "secret")


def is_never_touch(rel: str) -> bool:
    """``credentials.toml`` (any depth) — never read, never written."""
    return PurePosixPath(rel).name.lower() in NEVER_TOUCH_NAMES


def is_credential_file(rel: str) -> bool:
    """Name looks like it exists to carry credentials → contents withheld."""
    name = PurePosixPath(rel).name.lower()
    if name in _CREDENTIAL_NAMES or name.startswith(".env"):
        return True
    if name.endswith(_CREDENTIAL_SUFFIXES):
        return True
    stem = name.split(".", 1)[0]
    return any(word in stem for word in _CREDENTIAL_STEM_WORDS)


# --- key / value heuristics -----------------------------------------------

_SENSITIVE_KEY = re.compile(
    r"(token|secret|passw(?:or)?d|cred|cookie|bearer|private|"
    r"api[-_.]?key|access[-_.]?key|refresh|client[-_.]?secret|"
    r"session[-_.]?id|signing|ssh)",
    re.IGNORECASE,
)
# 'auth' counts, but not when it is the start of 'author'/'authorization'.
_AUTH_KEY = re.compile(r"auth(?!or)", re.IGNORECASE)

# token-ish *values*: long alnum-ish blobs, base64 blobs, JWTs, known
# vendor prefixes.
_LONG_BLOB = re.compile(r"^[A-Za-z0-9_\-]{24,}$")
_B64_BLOB = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")
_JWT = re.compile(r"^eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*$")
_PREFIXED = re.compile(
    r"^(sk|pk|ghp|gho|ghu|ghs|ghr|glpat|github_pat|xox[a-z]|dvn|devin|"
    r"AIza|ya29|hf|npm|pypi|slack)[-_.][A-Za-z0-9_\-.]{8,}$",
    re.IGNORECASE,
)

_MAX_VALUE_LEN = 80


def is_sensitive_key(key: str) -> bool:
    # '[0]' list-index segments and similar are never sensitive.
    if not key or key.startswith("["):
        return False
    return bool(_SENSITIVE_KEY.search(key) or _AUTH_KEY.search(key))


def is_sensitive_path(path: str) -> bool:
    """Any dotted key-path segment (or the whole leaf name) sensitive."""
    segments = re.split(r"[.\[\]]+", path)
    return any(is_sensitive_key(seg) for seg in segments if seg)


def looks_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    return bool(
        _LONG_BLOB.match(v)
        or _B64_BLOB.match(v)
        or _JWT.match(v)
        or _PREFIXED.match(v)
    )


def display_value(path: str, value: Any) -> str:
    """Human-readable value for diff output — masked when it could be a
    secret (sensitive key path, token-ish string), truncated when long."""
    if is_sensitive_path(path) or looks_secret(value):
        return REDACTED
    try:
        rendered = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        rendered = repr(value)
    if len(rendered) > _MAX_VALUE_LEN:
        rendered = rendered[: _MAX_VALUE_LEN - 1] + "…"
    return rendered


# --- free-text line masking (unified diffs of non-JSON files) --------------

# KEY=value / "key": "value" / -H "Authorization: Bearer x" shapes.
_KV_SECRET = re.compile(
    r"(?P<key>[A-Za-z0-9_\-.]*"
    r"(?:token|secret|passw(?:or)?d|cred|cookie|bearer|private|api[-_.]?key|"
    r"access[-_.]?key|auth(?!or)|client[-_.]?secret)"
    r"[A-Za-z0-9_\-.]*)"
    r"(?P<sep>\s*[:=]\s*[\"']?)"
    r"(?P<val>[^\s\"',}]+)",
    re.IGNORECASE,
)
# Bearer/Authorization headers mid-line.
_BEARER = re.compile(r"(bearer\s+)[A-Za-z0-9_\-.~+/=]+", re.IGNORECASE)
# standalone long blobs that are almost certainly tokens, not prose.
_STANDALONE_BLOB = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")


def mask_line(line: str) -> str:
    """Mask secrets inside a single diff line, preserving structure."""
    masked = _KV_SECRET.sub(
        lambda m: f"{m.group('key')}{m.group('sep')}{REDACTED}", line
    )
    masked = _BEARER.sub(lambda m: m.group(1) + REDACTED, masked)
    masked = _STANDALONE_BLOB.sub(REDACTED, masked)
    return masked
