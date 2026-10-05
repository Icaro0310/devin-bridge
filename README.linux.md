# devin-office — Linux guide

This guide covers Linux setup only. See [README.md](README.md) for features, shared commands, limitations, and the safety model.

Linux uses the extended runtime: local execution plus optional Devin VM/QwenPaw delegation when this artifact supports it.

## Prerequisites

- Python 3.10 or newer.
- Git for a source checkout.
- Devin Desktop or CLI on the machine whose sessions you want to view.

## Install

From a repository checkout, run the standalone read-only dashboard:

```bash
python3 daemon.py --port 8788
```

Open `http://localhost:8788`; the process stops with Ctrl+C.

## Devin paths

Session data normally lives under `${XDG_DATA_HOME:-$HOME/.local/share}/devin/cli/`; UI state and ACP stores under `${XDG_CONFIG_HOME:-$HOME/.config}/Devin/User/`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Environment notes

- Delegated runtime is optional; this guide installs local tooling only.
- Linux can use additional compute or Linux-compatible delegated tooling when available.
- macOS is planned but not claimed as tested.
- Optional scheduling uses `systemd --user` or cron; installation does not create jobs automatically.

## Troubleshooting

- Start the daemon from the repository directory with the OS-specific Python launcher shown above.
