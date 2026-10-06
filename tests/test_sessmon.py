import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sessmon  # noqa: E402

DDL = """
CREATE TABLE sessions (id TEXT PRIMARY KEY, working_directory TEXT NOT NULL,
  backend_type TEXT NOT NULL, model TEXT NOT NULL, agent_mode TEXT NOT NULL,
  created_at INTEGER NOT NULL, last_activity_at INTEGER NOT NULL,
  title TEXT, main_chain_id INTEGER, hidden INTEGER NOT NULL DEFAULT 0);
CREATE TABLE message_nodes (row_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL, node_id INTEGER NOT NULL, parent_node_id INTEGER,
  chat_message TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE tool_call_state (session_id TEXT NOT NULL, tool_call_id TEXT NOT NULL,
  tool_call_json TEXT, tool_call_update_json TEXT,
  PRIMARY KEY (session_id, tool_call_id));
"""


def _msg(role, text="", tools=None):
    return json.dumps({"role": role,
                       "content": [{"type": "text", "text": text}],
                       "tool_calls": tools or []})


def _tool(status):
    return json.dumps({"status": status})


class SessMonTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.locks = self.root / "locks"
        self.locks.mkdir()
        self.db = sqlite3.connect(str(self.root / "sessions.db"))
        self.db.executescript(DDL)
        self.now = int(time.time())

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def _session(self, sid, age=100, title="t", hidden=0):
        self.db.execute(
            "insert into sessions (id, working_directory, backend_type, model,"
            " agent_mode, created_at, last_activity_at, title, hidden)"
            " values (?,?,?,?,?,?,?,?,?)",
            (sid, "/home/u/proj", "cli", "swe-1", "bypass",
             self.now - age - 100, self.now - age, title, hidden))

    def _node(self, sid, role, text="", tools=None):
        self.db.execute(
            "insert into message_nodes (session_id, node_id, chat_message,"
            " created_at) values (?,?,?,?)",
            (sid, 1, _msg(role, text, tools), self.now))

    def _toolcall(self, sid, status):
        self.db.execute(
            "insert into tool_call_state (session_id, tool_call_id,"
            " tool_call_json, tool_call_update_json) values (?,?,?,?)",
            (sid, "t1", "{}", _tool(status)))

    def _collect(self, **kw):
        return {s["id"]: s for s in sessmon.collect_sessions(
            self.db, self.locks, self.now, **kw)}

    def test_running_when_recent_tool_turn(self):
        self._session("s-run", age=10)
        self._node("s-run", "assistant", "working", tools=[{"x": 1}])
        self._toolcall("s-run", "in_progress")
        self.assertEqual(self._collect()["s-run"]["status"], "running")

    def test_review_when_assistant_done(self):
        self._session("s-done", age=3600)
        self._node("s-done", "assistant", "Feito. Commit abc123 aplicado.")
        s = self._collect()["s-done"]
        self.assertEqual((s["status"], s["reason"]), ("review", "done"))

    def test_blocked_on_question_tail(self):
        self._session("s-q", age=3600)
        self._node("s-q", "assistant", "Tenho duas opções. Quer que eu siga?")
        s = self._collect()["s-q"]
        self.assertEqual((s["status"], s["reason"]), ("blocked", "question"))

    def test_blocked_on_pending_permission(self):
        self._session("s-perm", age=99999)
        self._node("s-perm", "assistant", "vou executar", tools=[{"x": 1}])
        self._toolcall("s-perm", "pending")
        s = self._collect()["s-perm"]
        self.assertEqual((s["status"], s["reason"]), ("blocked", "approval"))

    def test_blocked_when_user_unanswered(self):
        self._session("s-unans", age=99999)
        self._node("s-unans", "user", "faz isto")
        self.assertEqual(self._collect()["s-unans"]["reason"], "unanswered")

    def test_hidden_excluded_and_closed_override(self):
        self._session("s-hid", hidden=1)
        self._session("s-x", age=5000)
        self._node("s-x", "assistant", "done.")
        out = self._collect(closed={"s-x"})
        self.assertNotIn("s-hid", out)
        self.assertEqual(out["s-x"]["status"], "closed")

    def test_kanban_file_roundtrip(self):
        kf = self.root / "kanban.json"
        sessmon.set_closed(kf, "s-a", True)
        sessmon.set_closed(kf, "s-b", True)
        sessmon.set_closed(kf, "s-a", False)
        self.assertEqual(sessmon.load_closed(kf), {"s-b"})
        sess = [{"id": "s-b", "status": "review"},
                {"id": "s-c", "status": "running"}]
        sessmon.apply_closed(sess, {"s-b"})
        self.assertEqual(sess[0]["status"], "closed")
        self.assertEqual(sess[1]["status"], "running")

    def test_lock_held_free_and_missing(self):
        self.assertFalse(sessmon.lock_held(self.locks, "ghost"))
        (self.locks / "free.lock").write_text("1")
        self.assertFalse(sessmon.lock_held(self.locks, "free"))


if __name__ == "__main__":
    unittest.main()
