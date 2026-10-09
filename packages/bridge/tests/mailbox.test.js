import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  mailboxDir, checkPermissions, parseTask, listInbox, moveTo,
  MAX_TASK_BYTES,
} from "../src/mailbox.js";

let dir;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "mailbox-test-"));
});
afterEach(() => fs.rmSync(dir, { recursive: true, force: true }));

describe("mailboxDir", () => {
  it("creates the four stages", () => {
    const root = mailboxDir(dir);
    for (const s of ["inbox", "processing", "done", "failed"]) {
      assert.ok(fs.statSync(path.join(root, s)).isDirectory());
    }
  });
  it("is idempotent", () => {
    mailboxDir(dir);
    mailboxDir(dir); // no throw
  });
});

describe("checkPermissions", () => {
  it("accepts owner-only dirs", () => {
    const d = path.join(dir, "ok");
    fs.mkdirSync(d, { mode: 0o700 });
    checkPermissions(d); // no throw
  });
  it("rejects group/other-accessible dirs (POSIX)", {
    skip: process.platform === "win32",
  }, () => {
    const d = path.join(dir, "open");
    fs.mkdirSync(d, { mode: 0o755 });
    assert.throws(() => checkPermissions(d), /accessible by group\/other/);
  });
});

describe("parseTask", () => {
  const write = (name, content) => {
    const f = path.join(dir, name);
    fs.writeFileSync(f, content);
    return f;
  };

  it("parses a minimal task", () => {
    const r = parseTask(write("a.json", JSON.stringify({ task: "do it" })));
    assert.equal(r.ok, true);
    assert.equal(r.task.prompt, "do it");
    assert.equal(r.task.repo, null);
  });

  it("resolves repo to an absolute path", () => {
    const r = parseTask(write("b.json",
      JSON.stringify({ task: "x", repo: dir })));
    assert.equal(r.ok, true);
    assert.equal(r.task.repo, path.resolve(dir));
  });

  it("rejects invalid JSON", () => {
    assert.equal(parseTask(write("c.json", "{nope")).ok, false);
  });
  it("rejects non-object", () => {
    assert.equal(parseTask(write("d.json", "[1]")).ok, false);
    assert.equal(parseTask(write("e.json", "42")).ok, false);
  });
  it("rejects missing/empty task", () => {
    assert.equal(parseTask(write("f.json", "{}")).ok, false);
    assert.equal(parseTask(write("g.json", '{"task":"  "}')) .ok, false);
  });
  it("rejects oversized files", () => {
    const f = write("big.json",
      JSON.stringify({ task: "x".repeat(MAX_TASK_BYTES) }));
    const r = parseTask(f);
    assert.equal(r.ok, false);
    assert.match(r.error, /exceeds/);
  });
  it("rejects a repo that does not exist", () => {
    const r = parseTask(write("h.json",
      JSON.stringify({ task: "x", repo: "/no/such/dir-zzz" })));
    assert.equal(r.ok, false);
    assert.match(r.error, /does not exist/);
  });
});

describe("listInbox / moveTo", () => {
  it("lists .json files sorted by name", () => {
    const root = mailboxDir(dir);
    fs.writeFileSync(path.join(root, "inbox", "b.json"), "{}");
    fs.writeFileSync(path.join(root, "inbox", "a.json"), "{}");
    fs.writeFileSync(path.join(root, "inbox", "note.txt"), "x");
    const files = listInbox(root).map((f) => path.basename(f));
    assert.deepEqual(files, ["a.json", "b.json"]);
  });

  it("moves a file to another stage with a timestamp prefix", () => {
    const root = mailboxDir(dir);
    const f = path.join(root, "inbox", "a.json");
    fs.writeFileSync(f, "{}");
    const dst = moveTo(root, f, "done");
    assert.ok(!fs.existsSync(f));
    assert.ok(fs.existsSync(dst));
    assert.match(path.basename(dst), /-a\.json$/);
  });
});
