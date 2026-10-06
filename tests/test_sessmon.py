import fcntl
import json
import os
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
        self._fds = []

    def tearDown(self):
        self.db.close()
        for fd in self._fds:
            os.close(fd)
        self._tmp.cleanup()

    def _hold_lock(self, sid):
        """Simula um processo devin vivo: flock exclusivo no .lock."""
        p = self.locks / f"{sid}.lock"
        fd = os.open(str(p), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._fds.append(fd)

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

    def test_running_locked_tool_result_turn(self):
        # GUI a meio de um turno: último node gravado é um tool result —
        # turno ainda aberto, lock mantido, actividade fresca.
        self._session("s-tool", age=30)
        self._node("s-tool", "tool", "exit 0")
        self._hold_lock("s-tool")
        s = self._collect()["s-tool"]
        self.assertEqual((s["status"], s["reason"]), ("running", "working"))

    def test_running_locked_fresh_assistant_text(self):
        # Sessão GUI locked com escrita fresca na acp db (sessions.db atrasa):
        # último node é texto do assistant mas o processo está a trabalhar.
        self._session("s-acp", age=5000)
        self._node("s-acp", "assistant", "a analisar os resultados")
        self._hold_lock("s-acp")
        s = self._collect(activity={"s-acp": self.now - 20})["s-acp"]
        self.assertEqual(s["status"], "running")
        self.assertEqual(s["ageS"], 20)

    def test_running_gui_acp_fresh_no_lock(self):
        # Sessão GUI sem lock CLI mas a acp db dela acabou de ser escrita —
        # o Desktop está a trabalhar nela.
        self._session("s-gui", age=300)
        self._node("s-gui", "assistant", "texto parcial sem pergunta.")
        s = self._collect(activity={"s-gui": self.now - 10})["s-gui"]
        self.assertEqual(s["status"], "running")

    def test_running_gui_acp_tool_in_progress(self):
        # Sessão GUI com tool longa (sleep/watch): a acp db não escreve
        # enquanto a tool corre — o status in_progress é autoritativo.
        self._session("s-guilong", age=300)
        self._node("s-guilong", "tool", "partial")
        s = self._collect(activity={"s-guilong": self.now - 200},
                          acp_tool={"s-guilong": "in_progress"})["s-guilong"]
        self.assertEqual(s["status"], "running")

    def test_blocked_gui_acp_tool_pending(self):
        self._session("s-guip", age=300)
        self._node("s-guip", "assistant", "preciso de aprovação")
        s = self._collect(acp_tool={"s-guip": "pending"})["s-guip"]
        self.assertEqual((s["status"], s["reason"]), ("blocked", "approval"))

    def test_locked_stale_is_review(self):
        # Lock mantido mas sem actividade há muito → não é working.
        self._session("s-idle", age=5000)
        self._node("s-idle", "assistant", "Feito.")
        self._hold_lock("s-idle")
        self.assertEqual(self._collect()["s-idle"]["status"], "review")

    def test_blocked_locked_fresh_question(self):
        # Pergunta vence running mesmo com lock + actividade fresca.
        self._session("s-lq", age=10)
        self._node("s-lq", "assistant", "Quer que eu siga?")
        self._hold_lock("s-lq")
        s = self._collect()["s-lq"]
        self.assertEqual((s["status"], s["reason"]), ("blocked", "question"))

    def test_running_locked_in_progress_old(self):
        # Tool longa com lock: sem writes novos mas ainda a correr.
        self._session("s-long", age=600)
        self._node("s-long", "assistant", "a correr testes", tools=[{"x": 1}])
        self._toolcall("s-long", "in_progress")
        self._hold_lock("s-long")
        self.assertEqual(self._collect()["s-long"]["status"], "running")

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
