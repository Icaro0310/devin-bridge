# devin-bridge — Linux guide

This guide covers Linux setup only. See [README.md](README.md) for features, shared commands, limitations, and the safety model.

## Prerequisites

- Node.js 20 or newer and npm.

## Install

Install the Node.js CLI:

```bash
npm install --global 'https://github.com/Icaro0310/devin-bridge/archive/4ad4f8a6b07160a6a266c1724e1bc87a564b4b39.tar.gz'
```

## Devin paths

Session data normally lives under `${XDG_DATA_HOME:-$HOME/.local/share}/devin/cli/`; UI state and ACP stores under `${XDG_CONFIG_HOME:-$HOME/.config}/Devin/User/`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Platform notes

- Windows and Linux are the initial tested platforms.
- macOS is planned but not claimed as tested.

## Troubleshooting

- If the bridge command is missing, check that npm's global executable directory is on `PATH` (`npm config get prefix`).
