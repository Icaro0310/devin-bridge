"""Minimal JSONC reader — Devin config files allow ``//`` and ``/* */``
comments but not trailing commas. Same contract as devin-doctor's
``_strip_jsonc`` / ``_load_jsonc``, re-implemented so devin-switch stays
stdlib-only with no cross-package dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def strip_jsonc(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments while respecting string literals."""
    out: list[str] = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def load_jsonc(path: Path) -> Any:
    return json.loads(strip_jsonc(path.read_text(encoding="utf-8")))


def try_load_json_bytes(data: bytes) -> Any:
    """Parse bytes as JSON/JSONC; return ``None`` when not valid."""
    try:
        return json.loads(strip_jsonc(data.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
