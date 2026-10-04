// BR-3: file-based task intake ("mailbox"). No network listener — tasks are
// JSON files dropped into <state-dir>/mailbox/inbox/, processed in order by
// `devin-bridge intake`. Mailbox tasks are UNTRUSTED input: they only become
// a prompt inside a normal bridge session, so every capability still goes
// through the active policy (default `ask` = a human approves each step).
// Directories are created 0700 and task files are expected owner-readable.

import fs from "node:fs";
import path from "node:path";

export const STAGES = ["inbox", "processing", "done", "failed"];
export const MAX_TASK_BYTES = 64 * 1024;
export const MAX_TASK_LEN = 16_000;

export function mailboxDir(stateDir) {
  const root = path.join(stateDir, "mailbox");
  for (const s of STAGES) {
    fs.mkdirSync(path.join(root, s), { recursive: true, mode: 0o700 });
  }
  return root;
}

/** Best-effort POSIX-permission check (skipped on Windows). */
export function checkPermissions(dir) {
  if (process.platform === "win32") return;
  const st = fs.statSync(dir);
  if ((st.mode & 0o077) !== 0) {
    throw new Error(
      `mailbox dir ${dir} is accessible by group/other — ` +
      `chmod 700 it (tasks are untrusted input)`);
  }
}

/**
 * Parse + validate one task file. Returns {ok, task?, error?}.
 * Schema: {"task": "…", "repo"?: "<dir>", "model"?: "<id>", "meta"?: {…}}
 */
export function parseTask(file) {
  let raw;
  try {
    const st = fs.statSync(file);
    if (st.size > MAX_TASK_BYTES) {
      return { ok: false, error: `task file exceeds ${MAX_TASK_BYTES} bytes` };
    }
    raw = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return { ok: false, error: `unreadable/invalid JSON: ${e.message}` };
  }
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    return { ok: false, error: "task must be a JSON object" };
  }
  if (typeof raw.task !== "string" || !raw.task.trim()) {
    return { ok: false, error: "task.task (string) is required" };
  }
  if (raw.task.length > MAX_TASK_LEN) {
    return { ok: false, error: `task.task exceeds ${MAX_TASK_LEN} chars` };
  }
  const repo = raw.repo ? path.resolve(String(raw.repo)) : null;
  if (repo && !fs.existsSync(repo)) {
    return { ok: false, error: `task.repo does not exist: ${repo}` };
  }
  return {
    ok: true,
    task: {
      prompt: raw.task,
      repo,
      model: typeof raw.model === "string" ? raw.model : null,
      meta: typeof raw.meta === "object" && raw.meta ? raw.meta : {},
    },
  };
}

export function listInbox(root) {
  return fs.readdirSync(path.join(root, "inbox"))
    .filter((f) => f.endsWith(".json"))
    .sort() // deterministic FIFO by filename
    .map((f) => path.join(root, "inbox", f));
}

/** Move `file` (under inbox/) to `stage`, prefixing a timestamp. */
export function moveTo(root, file, stage) {
  const dst = path.join(
    root, stage, `${new Date().toISOString().replace(/[:.]/g, "-")}-${path.basename(file)}`);
  fs.renameSync(file, dst);
  return dst;
}

