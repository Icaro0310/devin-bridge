import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { credentialsPath, devinBin, devinBinCandidates } from "../src/acp-client.js";


test("Linux credentials follow XDG_DATA_HOME", () => {
  assert.equal(
    credentialsPath({
      platform: "linux",
      env: { XDG_DATA_HOME: "/xdg/data" },
      home: "/home/user",
    }),
    "/xdg/data/devin/credentials.toml",
  );
});

test("Windows credentials follow APPDATA", () => {
  assert.equal(
    credentialsPath({
      platform: "win32",
      env: { APPDATA: "C:\\Users\\user\\AppData\\Roaming" },
      home: "C:\\Users\\user",
    }),
    path.join("C:\\Users\\user\\AppData\\Roaming", "devin", "credentials.toml"),
  );
});

test("explicit credentials path overrides platform defaults", () => {
  assert.equal(
    credentialsPath({
      platform: "linux",
      env: { DEVIN_CREDENTIALS_PATH: "/custom/credentials.toml" },
      home: "/home/user",
    }),
    "/custom/credentials.toml",
  );
});

test("Linux CLI is resolved from PATH", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "devin-bin-"));
  const executable = path.join(directory, "devin");
  fs.writeFileSync(executable, "#!/bin/sh\nexit 0\n", { mode: 0o755 });
  assert.equal(devinBin({ platform: "linux", env: { PATH: directory } }), executable);
});

test("Windows bundle candidate follows LOCALAPPDATA", () => {
  const candidates = devinBinCandidates({
    platform: "win32",
    env: { LOCALAPPDATA: "C:\\Users\\user\\AppData\\Local" },
    home: "C:\\Users\\user",
  });
  assert.ok(candidates[0].endsWith("devin.exe"));
});
