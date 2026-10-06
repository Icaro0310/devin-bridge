# devin-bridge — Corporate Windows guide

This guide covers restricted Windows setup only. For unrestricted Windows, see [README.windows.md](README.windows.md); for features, shared commands, limitations, and the safety model, see [README.md](README.md).

Corporate Windows is a local-only environment: no Devin VM, QwenPaw, Slack dependency, external compute, workload delegation or required external integration.

## Prerequisites

- Node.js 20 or newer and npm.

## Install

Install the Node.js CLI:

```powershell
npm install --global "@icaro0310/devin-bridge"
```

## Devin paths

Session data normally lives under `%APPDATA%\devin\cli\`; UI state and ACP stores under `%APPDATA%\Devin\User\`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Environment notes

- Keep execution local; do not configure VM, QwenPaw, external compute or workload delegation.
- Registry-declared external integrations remain optional and are not installed by this guide.
- macOS is planned but not claimed as tested.

## Troubleshooting

- If the bridge command is missing, check that npm's global executable directory is on `PATH` (`npm config get prefix`).
