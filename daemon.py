#!/usr/bin/env python3
"""office-daemon — smoke test do devin-office.

Poll sessions.db (WAL, mode=ro) + jev_log.db e serve um WorldState JSON
em /api/state + o index.html. Zero deps (stdlib only).

Uso: python office/daemon.py [--port 8788]
"""
import glob
import json
import os
import re
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSIONS_DB = Path(os.environ.get("APPDATA", "")) / "devin" / "cli" / "sessions.db"
JEV_DB = ROOT.parent / "jev_log.db"
ACTIVE_WINDOW_S = 15 * 60  # sessão "viva" se teve atividade nos últimos 15 min
SUBAGENT_TTL_S = 30 * 60

AGENT_ID_RE = re.compile(r"agent_id=([0-9a-f\-]+)")
COMPLETION_RE = re.compile(r"agent_id=([0-9a-f\-]+) completed")


def ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=0.75)


def jload(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def inference_name(tc_json: dict) -> str:
    meta = tc_json.get("_meta") or {}
    return meta.get("cognition.ai/inferenceToolName") or tc_json.get("kind") or "?"


def display_event_title(title: str) -> str:
    return re.sub(r"[A-Za-z]:\\(?:[^\\\s]+\\)+", lambda _match: "…\\", title)


def collect_state() -> dict:
    now = int(time.time())
    state = {
        "ts": now,
        "agents": [],
        "services": {},
        "events": [],
    }
    if not SESSIONS_DB.exists():
        return state | {"error": f"sessions.db not found: {SESSIONS_DB}"}

    db = ro(SESSIONS_DB)
    sessions = db.execute(
        "select id, title, model, agent_mode, last_activity_at, working_directory, "
        "created_at, hidden from sessions where coalesce(hidden, 0)=0 "
        "and last_activity_at>=? order by last_activity_at desc limit 20",
        (now - ACTIVE_WINDOW_S,),
    ).fetchall()
    active_ids = [row[0] for row in sessions]
    per_session_tools = {}
    events = []
    completed_by_session = {}
    if active_ids:
        placeholders = ",".join("?" for _ in active_ids)
        tool_rows = db.execute(
            "select session_id, tool_call_json, tool_call_update_json, rowid "
            f"from tool_call_state where session_id in ({placeholders}) "
            "order by rowid desc limit 800",
            active_ids,
        ).fetchall()
        for sid, tj, tu, rid in reversed(tool_rows):
            d = jload(tj) or {}
            u = jload(tu) or {}
            entry = {
                "name": inference_name(d),
                "title": (d.get("title") or "")[:90],
                "kind": d.get("kind"),
                "status": u.get("status"),
                "raw": d.get("rawInput") or {},
                "rid": rid,
            }
            per_session_tools.setdefault(sid, []).append(entry)
            events.append((rid, sid, entry))

        # completions de subagentes (role=system na chain do pai)
        for sid, cm in db.execute(
            "select session_id, chat_message from message_nodes "
            f"where session_id in ({placeholders}) and chat_message "
            "like '%subagent_completion_notification%' "
            "order by rowid desc limit 300",
            active_ids,
        ):
            completed_by_session[sid] = completed_by_session.get(sid, 0) + len(
                COMPLETION_RE.findall(cm or "")
            )

    # sessions ativas → NPCs
    for sid, title, model, mode, last_act, cwd, created, hidden in sessions:
        if hidden or now - (last_act or 0) > ACTIVE_WINDOW_S:
            continue
        tools = per_session_tools.get(sid, [])
        last_tool = tools[-1] if tools else None
        subs = []
        n_completed = completed_by_session.get(sid, 0)
        n_spawned = 0
        for t in tools:
            if t["name"] == "run_subagent":
                n_spawned += 1
                # heurística smoke: completions ≥ spawns desta sessão → done
                state_sub = ("completed" if n_completed >= n_spawned
                             else "running")
                subs.append({
                    "profile": t["raw"].get("profile", "?"),
                    "title": t["raw"].get("title", "subagent"),
                    "state": state_sub,
                    "rid": t["rid"],
                })
        agent = {
            "id": sid,
            "kind": "agent",
            "name": "Devin",
            "title": (title or "")[:80],
            "model": model or "?",
            "project": (cwd or "").split("\\")[-1],
            "state": ("failed" if last_tool and last_tool["status"] == "failed"
                      else "idle" if now - (last_act or 0) > 120 else "working"),
            "currentTool": (last_tool["name"] if last_tool else None),
            "currentToolTitle": (last_tool["title"] if last_tool else ""),
            "toolCount": len(tools),
            "lastActivity": last_act,
            "subagents": subs,
        }
        state["agents"].append(agent)

        # MCP usage → service NPCs
        for t in tools:
            srv = t["raw"].get("server_name")
            if srv:
                svc = state["services"].setdefault(srv, {
                    "id": f"mcp:{srv}", "kind": "mcp", "name": srv,
                    "calls": 0, "lastTool": None, "state": "idle",
                })
                svc["calls"] += 1
                svc["lastTool"] = t["raw"].get("tool_name") or t["name"]
                svc["state"] = "active" if t["rid"] == (tools[-1]["rid"] if tools else -1) else svc["state"]

    # Jevin
    if JEV_DB.exists():
        try:
            jdb = ro(JEV_DB)
            row = jdb.execute(
                "select tool, choice, confidence, ts, cost from jev_decisions "
                "order by id desc limit 1"
            ).fetchone()
            total = jdb.execute("select count(*) from jev_decisions").fetchone()[0]
            if row:
                state["services"]["jevin"] = {
                    "id": "jev", "kind": "ambient", "name": "Jevin",
                    "state": "active",
                    "lastTool": f"{row[0]}→{row[1]} ({(row[2] or 0):.0%})",
                    "confidence": row[2],
                    "calls": total,
                }
        except sqlite3.Error:
            pass

    # ambient: heartbeat + gateways (sinais de vida dos ficheiros)
    hb = ROOT.parent / "heartbeat" / "state.json"
    if hb.exists():
        try:
            hbd = json.loads(hb.read_text(encoding="utf-8"))
            state["services"]["heartbeat"] = {
                "id": "ambient:heartbeat", "kind": "ambient", "name": "heartbeat",
                "state": "idle",
                "lastTool": f"{len(hbd.get('last_notified', {}))} watchers",
                "calls": len(hbd.get("last_notified", {})),
            }
        except Exception:
            pass

    # ticker de eventos: últimos 15 tool calls
    for rid, sid, e in events[-15:]:
        title = display_event_title(e["title"] or "")
        state["events"].insert(0, {
            "rid": rid, "session": sid,
            "text": f"{e['name']}: {title}".strip()[:110],
            "status": e["status"],
        })

    db.close()
    return state


INDEX = (ROOT / "index.html").read_bytes()
STATE_CACHE = {"ts": int(time.time()), "agents": [], "services": {}, "events": [], "loading": True}
STATE_LOCK = threading.Lock()


def cached_state() -> dict:
    with STATE_LOCK:
        return STATE_CACHE


def refresh_state_loop() -> None:
    global STATE_CACHE
    while True:
        try:
            next_state = collect_state()
        except Exception as exc:
            next_state = {"ts": int(time.time()), "agents": [], "services": {}, "events": [], "error": str(exc)}
        with STATE_LOCK:
            STATE_CACHE = next_state
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(cached_state()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path in ("/", "/index.html"):
            body = INDEX
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            body = b"404"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass


if __name__ == "__main__":
    port = 8788
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"devin-office smoke daemon -> http://localhost:{port}")
    print(f"sessions.db: {SESSIONS_DB} (exists={SESSIONS_DB.exists()})")
    threading.Thread(target=refresh_state_loop, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
