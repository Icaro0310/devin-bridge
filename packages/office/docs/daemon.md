# Running devin-office as a service

`devin-office` is a local dashboard: `daemon.py` polls `sessions.db` and
serves `WorldState` at `/api/state` plus `index.html` (stdlib only, zero
dependencies). Running it as a user service just formalizes the pattern
it already follows.

It is *almost* read-only: besides serving data it also exposes
`POST /api/kanban`, which persists session close/reopen marks to
`kanban.json`. That is the only write path — the store itself is never
mutated — and the service binds to localhost, so unattended serving is
still safe.

Platform setup lives in the OS-specific guides:

- **Linux (systemd user service):** [daemon-linux.md](daemon-linux.md)
- **Windows (Task Scheduler):** [daemon-windows.md](daemon-windows.md)
