/**
 * dispatch.js — repo→session mapping and task dispatch.
 *
 * Port of personal-agent-system/scripts/devin-repo-task.js: each repo
 * gets an isolated ACP session created with cwd=<repo-dir> (sessions
 * surface in Devin Desktop grouped by project directory). The repo→
 * sessionId mapping lives in a `.sessions.json` file so runs can resume.
 *
 * SECURITY: `.sessions.json` holds ids + cwd + timestamp only — never
 * tokens or credentials.
 */

import fs from "node:fs";
import path from "node:path";

/**
 * Persistent repo→sessionId map. Tolerant: a missing or corrupt file
 * loads as empty rather than crashing a dispatch.
 */
export class SessionMap {
  constructor(file, data = {}) {
    this.file = file;
    this._data = data;
  }

  static load(file) {
    try {
      const doc = JSON.parse(fs.readFileSync(file, "utf8"));
      return new SessionMap(file, doc && typeof doc === "object" ? doc : {});
    } catch {
      return new SessionMap(file, {});
    }
  }

  get(key) {
    return this._data[key];
  }

  /**
   * @param {string} key  repo key (basename)
   * @param {{sessionId: string, cwd: string}} entry — ids and paths only,
   *   never secrets; unknown keys are stripped on write.
   */
  set(key, { sessionId, cwd }) {
    this._data[key] = { sessionId, cwd, updatedAt: new Date().toISOString() };
  }

  remove(key) {
    delete this._data[key];
  }

  list() {
    return Object.entries(this._data).map(([repo, v]) => ({ repo, ...v }));
  }

  /** Atomic write: tmp file + rename (same volume → atomic). */
  save() {
    fs.mkdirSync(path.dirname(path.resolve(this.file)), { recursive: true });
    const tmp = `${this.file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this._data, null, 2));
    fs.renameSync(tmp, this.file);
  }
}

/**
 * Establish a session for `repoDir` using resume-or-create semantics:
 * - explicit `resumeId` wins over the stored mapping;
 * - a stored sessionId is tried via session/load first;
 * - any load failure (locked, missing, expired) falls back to session/new;
 * - the mapping is always written back with the live sessionId.
 *
 * @returns {Promise<{sessionId: string, resumed: boolean}>}
 */
export async function ensureSession(acp, repoDir, { map, resumeId } = {}) {
  const key = path.basename(path.resolve(repoDir));
  const existing = resumeId || map?.get(key)?.sessionId;

  if (existing) {
    try {
      await acp.loadSession(existing, repoDir);
      map?.set(key, { sessionId: acp.sessionId, cwd: path.resolve(repoDir) });
      return { sessionId: acp.sessionId, resumed: true };
    } catch {
      // fall through to session/new — locked/stale ids are expected churn
    }
  }
  await acp.newSession(repoDir);
  map?.set(key, { sessionId: acp.sessionId, cwd: path.resolve(repoDir) });
  return { sessionId: acp.sessionId, resumed: false };
}

/**
 * Full dispatch: ensure session for `repoDir`, persist the mapping to
 * `sessionsFile`, run `promptText`, return the prompt result plus repo
 * metadata. The caller owns the client lifecycle (start/init/stop).
 *
 * @returns prompt() result + {repo, sessionId, resumed}
 */
export async function runTask(acp, repoDir, {
  promptText,
  sessionsFile,
  resumeId,
  timeoutMs,
} = {}) {
  if (!fs.existsSync(repoDir)) throw new Error(`repo dir does not exist: ${repoDir}`);
  if (!promptText?.trim()) throw new Error("empty prompt");

  const key = path.basename(path.resolve(repoDir));
  const map = SessionMap.load(sessionsFile);
  const { sessionId, resumed } = await ensureSession(acp, repoDir, { map, resumeId });
  map.save();

  const res = await acp.prompt(promptText, { timeoutMs });
  return { repo: key, sessionId, resumed, ...res };
}
