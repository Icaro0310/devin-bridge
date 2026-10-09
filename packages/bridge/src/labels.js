/**
 * labels.js — origin/purpose labels for bridge-created sessions (BR-4).
 *
 * Downstream tools (devin-janitor classification, devin-dream
 * scorekeeping) need to recognise bridge-created/automation sessions
 * deterministically. Two complementary mechanisms:
 *
 * 1. `session/new` carries `_meta: {"devin-bridge": {origin, purpose,
 *    label}}` — `_meta` is the spec-sanctioned ACP extension point, so
 *    sending it is safe; whether the agent persists it is undocumented.
 * 2. A local sidecar `session-labels.json` under the bridge state dir
 *    maps sessionId → {label, origin, purpose, createdAt, cwd}. This is
 *    the authoritative, deterministic record — it exists whether or not
 *    the agent honours `_meta`.
 *
 * Labels are slugs (`origin:purpose`, each component
 * `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`) — never session content, prompts,
 * paths with secrets or prose. The charset/length restriction exists so
 * a label can never smuggle conversation data.
 *
 * Env:
 *   DEVIN_BRIDGE_STATE_DIR   overrides the sidecar directory entirely
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

/** Label applied when the caller passes no --label. */
export const DEFAULT_LABEL = "bridge:unlabeled";

/** Sidecar filename inside the bridge state dir. */
export const LABELS_FILENAME = "session-labels.json";

/**
 * Slug per label component: starts alphanumeric, then letters/digits/
 * `.`/`_`/`-`, max 64 chars. Deliberately excludes spaces and `:` so a
 * label cannot carry prose or extra structure.
 */
const LABEL_PART = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

/**
 * Parse a `origin:purpose` label string.
 * - unset/empty/non-string → DEFAULT_LABEL
 * - "origin" (no colon)   → "origin:unlabeled"
 * - "origin:purpose"      → split on the FIRST colon
 * Returns {label, origin, purpose}; throws on non-slug components.
 */
export function parseLabel(input) {
  const raw = (typeof input === "string" ? input : "").trim() || DEFAULT_LABEL;
  const idx = raw.indexOf(":");
  const origin = idx === -1 ? raw : raw.slice(0, idx);
  const purpose = idx === -1 ? "unlabeled" : raw.slice(idx + 1);
  if (!LABEL_PART.test(origin)) {
    throw new Error(
      `invalid label origin ${JSON.stringify(origin)} — expected a slug `
      + `([A-Za-z0-9._-], e.g. --label janitor:nightly)`,
    );
  }
  if (!LABEL_PART.test(purpose)) {
    throw new Error(
      `invalid label purpose ${JSON.stringify(purpose)} — expected a slug `
      + `([A-Za-z0-9._-], e.g. --label janitor:nightly)`,
    );
  }
  return { label: `${origin}:${purpose}`, origin, purpose };
}

/**
 * Bridge state directory (labels sidecar and future local state).
 * Resolution order: DEVIN_BRIDGE_STATE_DIR → platform default:
 *   win32  %LOCALAPPDATA%\devin-bridge
 *   darwin ~/Library/Application Support/devin-bridge
 *   linux  $XDG_STATE_HOME/devin-bridge (~/.local/state/devin-bridge)
 */
export function bridgeStateDir({
  platform = process.platform,
  env = process.env,
  home = os.homedir(),
} = {}) {
  if (env.DEVIN_BRIDGE_STATE_DIR) return path.resolve(env.DEVIN_BRIDGE_STATE_DIR);
  if (platform === "win32") {
    const local = env.LOCALAPPDATA || path.join(home, "AppData", "Local");
    return path.join(local, "devin-bridge");
  }
  if (platform === "darwin") {
    return path.join(home, "Library", "Application Support", "devin-bridge");
  }
  const stateHome = env.XDG_STATE_HOME || path.join(home, ".local", "state");
  return path.join(stateHome, "devin-bridge");
}

/** Absolute path of the labels sidecar for the resolved state dir. */
export function labelsFile(opts) {
  return path.join(bridgeStateDir(opts), LABELS_FILENAME);
}

/**
 * Persistent sessionId → label sidecar. Same durability contract as
 * SessionMap: missing/corrupt file loads empty, writes are atomic
 * (tmp + rename), only whitelisted metadata fields are persisted —
 * never prompts, tokens or session content.
 */
export class LabelStore {
  constructor(file, data = {}) {
    this.file = file;
    this._data = data;
  }

  static load(file) {
    try {
      const doc = JSON.parse(fs.readFileSync(file, "utf8"));
      const sessions = doc && typeof doc === "object" && doc.sessions
        && typeof doc.sessions === "object" ? doc.sessions : {};
      return new LabelStore(file, { version: 1, sessions });
    } catch {
      return new LabelStore(file, { version: 1, sessions: {} });
    }
  }

  get(sessionId) {
    return this._data.sessions[sessionId];
  }

  /**
   * @param {string} sessionId
   * @param {{label: string, origin: string, purpose: string, cwd?: string,
   *   createdAt?: string}} meta — whitelisted fields only; unknown keys
   *   are stripped on write. cwd is dispatch metadata (already public in
   *   .sessions.json), not session content.
   */
  record(sessionId, { label, origin, purpose, cwd, createdAt } = {}) {
    if (!sessionId || !origin || !purpose) return;
    this._data.sessions[sessionId] = {
      label: label || `${origin}:${purpose}`,
      origin,
      purpose,
      createdAt: createdAt || new Date().toISOString(),
      ...(cwd ? { cwd: path.resolve(cwd) } : {}),
    };
  }

  remove(sessionId) {
    delete this._data.sessions[sessionId];
  }

  list() {
    return Object.entries(this._data.sessions)
      .map(([sessionId, v]) => ({ sessionId, ...v }));
  }

  /** Atomic write: tmp file + rename (same volume → atomic). */
  save() {
    fs.mkdirSync(path.dirname(path.resolve(this.file)), { recursive: true });
    const tmp = `${this.file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this._data, null, 2));
    fs.renameSync(tmp, this.file);
  }
}
