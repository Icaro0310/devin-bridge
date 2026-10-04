import { describe, it, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_LABEL, LABELS_FILENAME, LabelStore, bridgeStateDir,
  labelsFile, parseLabel,
} from "../src/labels.js";
import { DevinAcp } from "../src/acp-client.js";
import { SessionMap, ensureSession, runTask } from "../src/dispatch.js";
import { Policy } from "../src/policy.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "fake-acp.mjs");
const FIXTURES = path.join(HERE, "fixtures");

function tmpdir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "db-label-"));
}

describe("parseLabel", () => {
  it("defaults to bridge:unlabeled when unset or non-string", () => {
    assert.equal(parseLabel(undefined).label, DEFAULT_LABEL);
    assert.equal(parseLabel("").label, DEFAULT_LABEL);
    assert.equal(parseLabel(true).label, DEFAULT_LABEL); // bare --label flag
    assert.deepEqual(parseLabel(null), {
      label: "bridge:unlabeled", origin: "bridge", purpose: "unlabeled",
    });
  });

  it("splits on the first colon into origin:purpose", () => {
    assert.deepEqual(parseLabel("janitor:nightly"), {
      label: "janitor:nightly", origin: "janitor", purpose: "nightly",
    });
  });

  it("a bare slug becomes origin:unlabeled", () => {
    assert.equal(parseLabel("dream").label, "dream:unlabeled");
  });

  it("accepts dots, dashes and underscores", () => {
    assert.equal(
      parseLabel("ci_runner.v2:score-keep_v3").label,
      "ci_runner.v2:score-keep_v3",
    );
  });

  it("rejects non-slug components (labels can never carry content)", () => {
    for (const bad of [
      "a:b:c",               // extra colon in purpose
      ":purpose",            // empty origin
      "origin:",             // empty purpose
      "run the tests:fix",   // prose in origin
      "a:fix it",            // whitespace
      "../etc:x",            // path traversal shape
      "a;" + "b".repeat(80), // >64 chars
    ]) {
      assert.throws(() => parseLabel(bad), /invalid label/);
    }
  });
});

describe("bridgeStateDir / labelsFile", () => {
  it("DEVIN_BRIDGE_STATE_DIR wins", () => {
    assert.equal(
      bridgeStateDir({ platform: "linux", env: { DEVIN_BRIDGE_STATE_DIR: "x/state" }, home: "/h" }),
      path.resolve("x/state"),
    );
  });

  it("Linux follows XDG_STATE_HOME (default ~/.local/state)", () => {
    assert.equal(
      bridgeStateDir({ platform: "linux", env: { XDG_STATE_HOME: "/xdg/state" }, home: "/h" }),
      path.join("/xdg/state", "devin-bridge"),
    );
    assert.equal(
      bridgeStateDir({ platform: "linux", env: {}, home: "/h" }),
      path.join("/h", ".local", "state", "devin-bridge"),
    );
  });

  it("Windows follows LOCALAPPDATA, darwin uses Application Support", () => {
    assert.equal(
      bridgeStateDir({ platform: "win32", env: { LOCALAPPDATA: "C:\\Local" }, home: "C:\\u" }),
      path.join("C:\\Local", "devin-bridge"),
    );
    assert.equal(
      bridgeStateDir({ platform: "darwin", env: {}, home: "/u" }),
      path.join("/u", "Library", "Application Support", "devin-bridge"),
    );
  });

  it("labelsFile resolves inside the state dir", () => {
    assert.equal(
      labelsFile({ platform: "linux", env: { DEVIN_BRIDGE_STATE_DIR: "/s" }, home: "/h" }),
      path.join(path.resolve("/s"), LABELS_FILENAME),
    );
  });
});

describe("LabelStore persistence", () => {
  it("missing/corrupt/badly-shaped files load as empty store", () => {
    const dir = tmpdir();
    assert.deepEqual(LabelStore.load(path.join(dir, "nope.json")).list(), []);

    const bad = path.join(dir, "bad.json");
    fs.writeFileSync(bad, "{not json");
    assert.deepEqual(LabelStore.load(bad).list(), []);

    const wrong = path.join(dir, "wrong.json");
    fs.writeFileSync(wrong, JSON.stringify({ sessions: "nope" }));
    assert.deepEqual(LabelStore.load(wrong).list(), []);
  });

  it("record/save/reload round-trips whitelisted metadata only", () => {
    const dir = tmpdir();
    const f = path.join(dir, LABELS_FILENAME);
    const s = LabelStore.load(f);
    s.record("s-1", {
      label: "janitor:nightly", origin: "janitor", purpose: "nightly",
      cwd: "/repo/x", createdAt: "2026-01-01T00:00:00.000Z",
      promptText: "MUST NOT PERSIST", token: "secret",
    });
    s.save();
    const raw = JSON.parse(fs.readFileSync(f, "utf8"));
    assert.equal(raw.version, 1);
    assert.deepEqual(Object.keys(raw.sessions["s-1"]).sort(), [
      "createdAt", "cwd", "label", "origin", "purpose",
    ]);
    const s2 = LabelStore.load(f);
    assert.equal(s2.get("s-1").label, "janitor:nightly");
    assert.equal(s2.list()[0].sessionId, "s-1");
  });

  it("record is a no-op without sessionId or parsed origin/purpose", () => {
    const s = LabelStore.load(path.join(tmpdir(), LABELS_FILENAME));
    s.record(null, { origin: "a", purpose: "b" });
    s.record("s-1", { cwd: "/x" });
    assert.equal(s.list().length, 0);
  });

  it("save is atomic and creates parent dirs", () => {
    const f = path.join(tmpdir(), "deep/nested", LABELS_FILENAME);
    const s = LabelStore.load(f);
    s.record("s-1", { origin: "a", purpose: "b" });
    s.save();
    assert.ok(fs.existsSync(f));
    assert.ok(!fs.existsSync(`${f}.tmp`));
  });
});

const clients = [];
after(() => { for (const c of clients.splice(0)) c.stop(); });
async function acpFor(repoDir) {
  const acp = new DevinAcp({
    bin: process.execPath,
    args: [FIXTURE],
    cwd: FIXTURES,
    token: "test-token",
    policy: Policy.default({ root: repoDir }),
    timeoutMs: 15000,
  });
  acp.start();
  await acp.init();
  clients.push(acp);
  return acp;
}

describe("session/new _meta (option 1)", () => {
  it("sends devin-bridge origin/purpose under _meta", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "meta-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    await acp.newSession(repo, {
      label: { label: "janitor:nightly", origin: "janitor", purpose: "nightly" },
    });
    const res = await acp.prompt("DUMP_SESSION_NEW");
    const params = JSON.parse(res.text.slice("NEW_PARAMS:".length));
    assert.equal(params.cwd, repo);
    assert.deepEqual(params._meta["devin-bridge"], {
      origin: "janitor", purpose: "nightly", label: "janitor:nightly",
    });
  });

  it("omits _meta when no label is given", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "meta-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    await acp.newSession(repo);
    const res = await acp.prompt("DUMP_SESSION_NEW");
    const params = JSON.parse(res.text.slice("NEW_PARAMS:".length));
    assert.equal(params._meta, undefined);
  });
});

describe("dispatch sidecar (option 2)", () => {
  it("ensureSession records the label only for sessions it creates", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    const store = LabelStore.load(path.join(dir, LABELS_FILENAME));

    const out = await ensureSession(acp, repo, {
      map, labelStore: store,
      label: parseLabel("janitor:classification"),
    });
    assert.equal(out.resumed, false);
    assert.equal(store.get("fx-new-1").label, "janitor:classification");
    assert.equal(store.get("fx-new-1").cwd, path.resolve(repo));
  });

  it("resume path neither sends _meta nor touches the sidecar", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "my-repo");
    fs.mkdirSync(repo);
    const acp = await acpFor(repo);
    const map = SessionMap.load(path.join(dir, ".sessions.json"));
    map.set("my-repo", { sessionId: "fx-old", cwd: repo });
    const store = LabelStore.load(path.join(dir, LABELS_FILENAME));

    const out = await ensureSession(acp, repo, {
      map, labelStore: store, label: parseLabel("bridge:x"),
    });
    assert.equal(out.resumed, true);
    assert.equal(store.list().length, 0); // resumed sessions keep their original label
  });

  it("runTask persists the label sidecar alongside .sessions.json", async () => {
    const dir = tmpdir();
    const repo = path.join(dir, "task-repo");
    fs.mkdirSync(repo);
    const labelsPath = path.join(dir, LABELS_FILENAME);
    const acp = await acpFor(repo);
    const res = await runTask(acp, repo, {
      promptText: "hello",
      sessionsFile: path.join(dir, ".sessions.json"),
      timeoutMs: 15000,
      label: parseLabel("dream:scorekeeping"),
      labelStore: LabelStore.load(labelsPath),
    });
    assert.equal(res.sessionId, "fx-new-1");
    const reloaded = LabelStore.load(labelsPath);
    assert.equal(reloaded.get("fx-new-1").label, "dream:scorekeeping");
    assert.equal(reloaded.get("fx-new-1").origin, "dream");
  });
});
