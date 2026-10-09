import { describe, it, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SessionMap, ensureSession, runTask } from "../src/dispatch.js";
import { DevinAcp } from "../src/acp-client.js";
import { Policy } from "../src/policy.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "fake-acp.mjs");
const FIXTURES = path.join(HERE, "fixtures");

function tmpdir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "db-map-"));
}

function makeAcp(repoDir) {
  const acp = new DevinAcp({
    bin: process.execPath,
    args: [FIXTURE],
    cwd: FIXTURES,
    token: "test-token",
    policy: Policy.default({ root: repoDir }),
    timeoutMs: 15000,
  });
  acp.start();
  return acp.init();
}

const clients = [];
after(() => { for (const c of clients.splice(0)) c.stop(); });
async function acpFor(repoDir) {
  const c = await makeAcp(repoDir);
  clients.push(c);
  return c;
}

describe("SessionMap persistence", () => {
  it("missing file loads as empty map", () => {
    const m = SessionMap.load(path.join(tmpdir(), "nope.json"));
    assert.deepEqual(m.list(), []);
  });

  it("corrupt JSON loads as empty map (tolerant)", () => {
    const f = path.join(tmpdir(), ".sessions.json");
    fs.writeFileSync(f, "{not json");
    assert.deepEqual(SessionMap.load(f).list(), []);
  });

  it("set/save/reload round-trips ids, cwd and timestamp only", () => {
    const dir = tmpdir();
    const f = path.join(dir, ".sessions.json");
    const m = SessionMap.load(f);
    m.set("devin-bridge", { sessionId: "s-1", cwd: "C:/repos/devin-bridge" });
    m.save();
    const raw = JSON.parse(fs.readFileSync(f, "utf8"));
    assert.equal(raw["devin-bridge"].sessionId, "s-1");
    assert.equal(raw["devin-bridge"].cwd, "C:/repos/devin-bridge");
    assert.ok(raw["devin-bridge"].updatedAt);
    // security: mapping file must hold ids only — no token-shaped keys
    assert.deepEqual(Object.keys(raw["devin-bridge"]).sort(), ["cwd", "sessionId", "updatedAt"]);
    const m2 = SessionMap.load(f);
    assert.equal(m2.get("devin-bridge").sessionId, "s-1");
  });

  it("save is atomic (no .tmp left behind) and creates parent dirs", () => {
    const f = path.join(tmpdir(), "deep/nested/.sessions.json");
    const m = SessionMap.load(f);
    m.set("k", { sessionId: "x", cwd: "/x" });
    m.save();
    assert.ok(fs.existsSync(f));
    assert.ok(!fs.existsSync(`${f}.tmp`));
  });

  it("remove drops a repo entry", () => {
    const m = SessionMap.load(path.join(tmpdir(), ".sessions.json"));
    m.set("a", { sessionId: "1", cwd: "/a" });
    m.remove("a");
    assert.equal(m.get("a"), undefined);
  });
});

describe("ensureSession resume logic", () => {
  it("creates a new session when no mapping exists", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    const out = await ensureSession(acp, repo, { map });
    assert.equal(out.resumed, false);
    assert.equal(out.sessionId, "fx-new-1");
    assert.equal(map.get("my-repo").sessionId, "fx-new-1");
  });

  it("resumes a mapped session", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    map.set("my-repo", { sessionId: "fx-old", cwd: repo });
    const out = await ensureSession(acp, repo, { map });
    assert.equal(out.resumed, true);
    assert.equal(out.sessionId, "fx-old");
    assert.equal(acp.sessionId, "fx-old");
  });

  it("falls back to new session when resume fails (session_locked)", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    map.set("my-repo", { sessionId: "fx-locked", cwd: repo });
    const out = await ensureSession(acp, repo, { map });
    assert.equal(out.resumed, false);
    assert.equal(out.sessionId, "fx-new-1");
    assert.equal(map.get("my-repo").sessionId, "fx-new-1");
  });

  it("explicit resumeId wins over the mapping", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    map.set("my-repo", { sessionId: "fx-old", cwd: repo });
    const out = await ensureSession(acp, repo, { map, resumeId: "fx-other" });
    assert.equal(out.sessionId, "fx-other");
  });
});

describe("runTask end-to-end", () => {
  it("establishes session, persists mapping, returns prompt result", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "task-repo");
    fs.mkdirSync(repo);
    const sessionsFile = path.join(dir, ".sessions.json");
    const acp = await acpFor(repo);
    const res = await runTask(acp, repo, {
      promptText: "hello",
      sessionsFile,
      timeoutMs: 15000,
    });
    assert.equal(res.sessionId, "fx-new-1");
    assert.equal(res.text, "echo: hello");
    assert.equal(res.repo, "task-repo");
    const map = SessionMap.load(sessionsFile);
    assert.equal(map.get("task-repo").sessionId, "fx-new-1");
  });
});
