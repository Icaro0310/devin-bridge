#!/usr/bin/env node
/**
 * devin-bridge — policy-gated bridge that drives `devin.exe acp`.
 *
 * Commands:
 *   new <repo-dir>                 create an isolated session (updates .sessions.json)
 *   resume <repo-dir> [--resume id]  reconnect to a mapped/explicit session
 *   prompt <repo-dir> <text>|--file f  send a prompt, stream the reply
 *   sessions [--json]              list repo→sessionId mappings
 *   policy --show|--init|--check <cap> <target>  inspect the permission policy
 *
 * Global options:
 *   --sessions-file <f>   mapping file (default ./.sessions.json)
 *   --policy <f>          policy file (default ./policy.json if present,
 *                         else the fail-closed built-in: everything asks)
 *   --bin <path>          devin.exe path (default: DEVIN_CLI_PATH/autodetect)
 *   --timeout-ms <n>      per-call timeout (default 300000; prompt waits up to 45min)
 *   --yes                 auto-approve policy "ask" prompts (headless runs)
 *   --help
 */

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { DevinAcp } from "../src/acp-client.js";
import { Policy, examplePolicyDoc } from "../src/policy.js";
import { SessionMap, ensureSession, runTask } from "../src/dispatch.js";

const CAPS = ["terminal", "fsRead", "fsWrite", "network"];

function parseArgs(argv) {
  const opts = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { opts._.push(a); continue; }
    const [k, inline] = a.slice(2).split("=", 2);
    if (inline !== undefined) { opts[k] = inline; continue; }
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith("--")) { opts[k] = next; i++; }
    else opts[k] = true;
  }
  return opts;
}

function usage(exitCode = 0) {
  console.log(`devin-bridge <command> [args] [options]

Commands:
  new <repo-dir>                    create a session for the repo (records mapping)
  resume <repo-dir> [--resume <id>] reconnect to a stored/explicit session
  prompt <repo-dir> <text>          send a prompt (or --file <f>), stream the reply
  sessions [--json]                 list repo -> session mappings
  policy --show                     print the effective policy
  policy --init [--force]           write ./policy.json with documented defaults
  policy --check <cap> <target>     decision for terminal|fsRead|fsWrite|network

Options: --sessions-file f --policy f --bin path --timeout-ms n --yes --help`);
  process.exit(exitCode);
}

function loadPolicy(opts) {
  const file = opts.policy || (fs.existsSync("policy.json") ? "policy.json" : null);
  if (file) {
    console.error(`[policy] ${path.resolve(file)}`);
    return Policy.load(file, { root: process.cwd() });
  }
  console.error("[policy] built-in default (everything requires asking)");
  return Policy.default();
}

/** Interactive askHandler: explicit y/yes approves, anything else denies. */
function interactiveAsker() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stderr });
  process.on("exit", () => rl.close());
  return (req) => new Promise((resolve) => {
    const desc = req.command ?? req.path ?? req.reason ?? req.capability;
    rl.question(`[policy:ask] agent wants ${req.capability} ${desc} — allow? [y/N] `, (ans) => {
      resolve(/^y(es)?$/i.test(ans.trim()) ? "allow" : "deny");
    });
  });
}

function makeClient(opts, { forPrompt = false } = {}) {
  const askHandler = opts.yes
    ? async () => "allow"
    : (process.stdin.isTTY && process.stderr.isTTY ? interactiveAsker() : null);
  const onNotification = forPrompt
    ? (msg) => {
        const upd = msg.params?.update;
        if (msg.method === "session/update" && upd?.sessionUpdate === "agent_message_chunk"
            && upd.content?.type === "text") {
          process.stderr.write(upd.content.text); // live stream; stdout stays clean
        }
      }
    : null;
  const acp = new DevinAcp({
    bin: opts.bin || undefined,
    cwd: process.cwd(),
    policy: loadPolicy(opts),
    askHandler,
    timeoutMs: opts["timeout-ms"] ? Number(opts["timeout-ms"]) : undefined,
    onNotification,
  });
  acp.start();
  return acp;
}

const CMDS = {
  async new(opts) {
    const repoDir = opts._[0];
    if (!repoDir) usage(1);
    const abs = path.resolve(repoDir);
    if (!fs.existsSync(abs)) throw new Error(`repo dir does not exist: ${abs}`);
    const acp = makeClient(opts);
    try {
      await acp.init();
      await acp.newSession(abs);
      const file = opts["sessions-file"] || ".sessions.json";
      const map = SessionMap.load(file);
      map.set(path.basename(abs), { sessionId: acp.sessionId, cwd: abs });
      map.save();
      if (opts.model) await acp.setModel(opts.model);
      console.log(JSON.stringify({
        repo: path.basename(abs), sessionId: acp.sessionId,
        models: acp.listModels(), model: acp.currentModel(),
      }, null, 2));
    } finally { acp.stop(); }
  },

  async resume(opts) {
    const repoDir = opts._[0];
    if (!repoDir) usage(1);
    const abs = path.resolve(repoDir);
    if (!fs.existsSync(abs)) throw new Error(`repo dir does not exist: ${abs}`);
    const acp = makeClient(opts);
    try {
      await acp.init();
      const file = opts["sessions-file"] || ".sessions.json";
      const map = SessionMap.load(file);
      const out = await ensureSession(acp, abs, { map, resumeId: opts.resume });
      map.save();
      console.log(JSON.stringify({
        repo: path.basename(abs), ...out, model: acp.currentModel(),
      }, null, 2));
    } finally { acp.stop(); }
  },

  async prompt(opts) {
    const repoDir = opts._[0];
    if (!repoDir) usage(1);
    const abs = path.resolve(repoDir);
    const promptText = opts.file
      ? fs.readFileSync(opts.file, "utf8")
      : opts._.slice(1).join(" ");
    const acp = makeClient(opts, { forPrompt: true });
    try {
      await acp.init();
      const res = await runTask(acp, abs, {
        promptText,
        sessionsFile: opts["sessions-file"] || ".sessions.json",
        resumeId: opts.resume,
        timeoutMs: opts["timeout-ms"] ? Number(opts["timeout-ms"]) : 45 * 60 * 1000,
      });
      process.stderr.write("\n");
      console.log("===== RESULT =====");
      console.log(JSON.stringify({
        repo: res.repo, sessionId: res.sessionId, resumed: res.resumed,
        model: res.modelLabel, stopReason: res.stopReason,
        cost: res.cost, timedOut: res.timedOut,
      }, null, 2));
      console.log("===== TEXT =====");
      console.log(res.text);
    } finally { acp.stop(); }
  },

  sessions(opts) {
    const file = opts["sessions-file"] || ".sessions.json";
    const map = SessionMap.load(file);
    if (opts.json) return console.log(JSON.stringify(map.list(), null, 2));
    if (!map.list().length) return console.log(`(no sessions in ${path.resolve(file)})`);
    for (const e of map.list()) {
      console.log(`${e.repo}\t${e.sessionId}\t${e.updatedAt}\t${e.cwd}`);
    }
  },

  policy(opts) {
    const file = opts.policy || "policy.json";
    if (opts.init !== undefined) {
      if (fs.existsSync(file) && !opts.force) {
        throw new Error(`${file} already exists (use --force to overwrite)`);
      }
      fs.writeFileSync(file, JSON.stringify(examplePolicyDoc(), null, 2) + "\n");
      return console.log(`wrote ${path.resolve(file)}`);
    }
    if (opts.check !== undefined) {
      const [cap, target] = [opts.check === true ? opts._[0] : opts.check,
        opts.check === true ? opts._[1] : opts._[0]];
      const p = loadPolicy(opts);
      const fn = { terminal: "checkTerminal", fsRead: "checkFsRead",
        fsWrite: "checkFsWrite", network: "checkNetwork" }[cap];
      if (!fn || target === undefined) {
        throw new Error(`usage: policy --check <${CAPS.join("|")}> <target>`);
      }
      return console.log(JSON.stringify({ capability: cap, target, decision: p[fn](target) }));
    }
    // default: --show
    const p = loadPolicy(opts);
    console.log(JSON.stringify(p.toJSON(), null, 2));
  },
};

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const cmd = opts._.shift();
  if (opts.help || !cmd) usage(cmd ? 0 : 0);
  const fn = CMDS[cmd];
  if (!fn) {
    console.error(`unknown command: ${cmd}`);
    usage(1);
  }
  await fn(opts);
}

main().catch((e) => {
  // Never include credential material in error output.
  console.error(`FATAL: ${e.message}`);
  process.exit(1);
});
