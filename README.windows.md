# devin-office — Windows guide

This guide covers Windows setup only. See [README.md](README.md) for features, shared commands, limitations, and the safety model.

## Prerequisites

- Python 3.10 or newer.
- Git for a source checkout.
- Devin Desktop or CLI on the machine whose sessions you want to view.

## Install

From a repository checkout, run the standalone read-only dashboard:

```powershell
py -3 daemon.py --port 8788
```

Open `http://localhost:8788`; the process stops with Ctrl+C.

## Devin paths

Session data normally lives under `%APPDATA%\devin\cli\`; UI state and ACP stores under `%APPDATA%\Devin\User\`.
Use the tool's documented `--data-dir` or `--config-dir` flags for non-default locations.

## Platform notes

- Windows and Linux are the initial tested platforms.
- macOS is planned but not claimed as tested.

## Troubleshooting

- Start the daemon from the repository directory with the OS-specific Python launcher shown above.
