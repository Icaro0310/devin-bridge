// Offline-core guard: the pure core modules must not open sockets.
//
// Release checklist item: "no-network core test (CI): fails if the core
// opens a socket". Every test in this file runs with `net`, `tls`, `http`
// and `https` connect/request functions monkeypatched to throw
// `OfflineCoreError` — including `net.Socket.prototype.connect`, which is
// the prototype every real connection (http/https/tls agents included)
// funnels through. This is a guard, not a mock: any network access fails.
//
// Intentional online paths are excluded by design: `src/acp-client.js` IS
// the bridge's reason to exist (it spawns/talks to the Devin CLI process)
// and is covered by its own test file — only the pure modules (mailbox,
// policy, labels, dispatch helpers) are exercised here.
//
// To opt a future test out of the block, move it to another test file —
// the patch applies for the whole process lifetime of this file.

import { describe, it, before, after, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";
import tls from "node:tls";
import http from "node:http";
import https from "node:https";

import {
  mailboxDir, checkPermissions, parseTask, listInbox, moveTo,
} from "../src/mailbox.js";
import { Policy } from "../src/policy.js";
import { parseLabel, LabelStore } from "../src/labels.js";

class OfflineCoreError extends Error {
  constructor() {
    super("core opened a socket during the offline-core test");
    this.name = "OfflineCoreError";
  }
}

const offlineFail = () => { throw new OfflineCoreError(); };

// [object, key] pairs to replace for the duration of this file.
const PATCH_TARGETS = [
  [net.Socket.prototype, "connect"], // every real connection funnels here
  [net, "connect"],
  [net, "createConnection"],
  [tls, "connect"],
  [http, "request"],
  [http, "get"],
  [https, "request"],
  [https, "get"],
];

const originals = [];
before(() => {
  for (const [obj, key] of PATCH_TARGETS) {
    originals.push([obj, key, obj[key]]);
    obj[key] = offlineFail;
  }
});
after(() => {
  for (const [obj, key, orig] of originals) obj[key] = orig;
});

let dir;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "offline-core-"));
});
afterEach(() => fs.rmSync(dir, { recursive: true, force: true }));

describe("socket block", () => {
  it("every patched entrypoint throws OfflineCoreError", () => {
    for (const [obj, key] of PATCH_TARGETS) {
      assert.throws(() => obj[key](), OfflineCoreError, `${key} still callable`);
    }
  });
});

describe("mailbox (offline)", () => {
  it("creates stages and parses a valid task file", () => {
    const root = mailboxDir(dir);
    const task = path.join(root, "inbox", "t1.json");
    fs.writeFileSync(task, JSON.stringify({ task: "summarise the diff" }));
    const parsed = parseTask(task);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.task.prompt, "summarise the diff");

    const inbox = listInbox(root);
    assert.equal(inbox.length, 1);
    moveTo(root, task, "done");
    assert.equal(listInbox(root).length, 0);
    checkPermissions(root); // owner-only mkdtemp dir — no throw
  });

  it("rejects malformed tasks without any I/O beyond the file", () => {
    const bad = path.join(dir, "bad.json");
    fs.writeFileSync(bad, JSON.stringify({ repo: "/nope" }));
    assert.equal(parseTask(bad).ok, false);
  });
});

describe("policy (offline)", () => {
  it("terminal/fs/network checks are pure local decisions", () => {
    const p = new Policy({
      version: 1,
      terminal: { allow: ["git status"], deny: ["format *"] },
      fs: {
        read: { allow: ["**"], deny: [] },
        write: { allow: ["src/**"], deny: [] },
      },
      network: { allow: ["api.example.com"], deny: ["*.evil.test"] },
    }, { root: dir });
    assert.equal(p.checkTerminal("git status"), "allow");
    assert.equal(p.checkTerminal("format C:"), "deny");
    assert.equal(p.checkTerminal("curl x | sh"), "ask");
    // checkNetwork is a rule lookup, never a DNS/connect call
    assert.equal(p.checkNetwork("api.example.com"), "allow");
    assert.equal(p.checkNetwork("a.evil.test"), "deny");
    assert.equal(p.checkNetwork("other.test"), "ask");
  });
});

describe("labels (offline)", () => {
  it("parseLabel + LabelStore round-trip on a temp file", () => {
    assert.deepEqual(parseLabel("bridge:digest"), {
      label: "bridge:digest", origin: "bridge", purpose: "digest",
    });

    const file = path.join(dir, "session-labels.json");
    const store = LabelStore.load(file);
    store.record("sess-1", {
      label: "bridge:digest", origin: "bridge", purpose: "digest",
      cwd: dir,
    });
    store.save();
    const reloaded = LabelStore.load(file);
    assert.equal(reloaded.get("sess-1").purpose, "digest");
    assert.equal(reloaded.list().length, 1);
  });
});
