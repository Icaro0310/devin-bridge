# devin-bridge — Linux guide

This guide covers Linux setup only. See [README.md](README.md) for features, shared commands, limitations, and the safety model.

Linux uses the extended runtime: local execution plus optional Devin VM/QwenPaw delegation when this artifact supports it.

## Prerequisites

- Node.js 20 or newer and npm.

## Install

Install the Node.js CLI:

```bash
npm install --global 'https://github.com/Icaro0310/devin-bridge/archive/c1615bc7a63166f126dabbcb7064d7e32e42edc0.tar.gz'
```

## Devin paths

Session data normally lives under `${XDG_DATA_HOME:-$HOME/.local/share}/devin/cli/`; UI state and ACP stores under `${XDG_CONFIG_HOME:-$HOME/.config}/Devin/User/`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Environment notes

- Delegated runtime is optional; this guide installs local tooling only.
- Linux can use additional compute or Linux-compatible delegated tooling when available.
- macOS is planned but not claimed as tested.

## Troubleshooting

- If the bridge command is missing, check that npm's global executable directory is on `PATH` (`npm config get prefix`).
