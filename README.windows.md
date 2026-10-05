# devin-bridge — Personal Windows guide

This guide covers unrestricted Windows setup. For restricted machines, see [README.corporate-windows.md](README.corporate-windows.md); for features, shared commands, limitations, and the safety model, see [README.md](README.md).

Personal Windows uses the extended runtime: local execution plus optional Devin VM/QwenPaw delegation when this artifact supports it.

## Prerequisites

- Node.js 20 or newer and npm.

## Install

Install the Node.js CLI:

```powershell
npm install --global "https://github.com/Icaro0310/devin-bridge/archive/c1615bc7a63166f126dabbcb7064d7e32e42edc0.tar.gz"
```

## Devin paths

Session data normally lives under `%APPDATA%\devin\cli\`; UI state and ACP stores under `%APPDATA%\Devin\User\`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Environment notes

- Delegated runtime is optional; this guide installs local tooling only.
- Corporate Windows is a separate local-only environment.
- macOS is planned but not claimed as tested.

## Troubleshooting

- If the bridge command is missing, check that npm's global executable directory is on `PATH` (`npm config get prefix`).
