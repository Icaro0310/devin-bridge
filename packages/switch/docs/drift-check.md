# Scheduled drift check (notification only)

`devin-switch` has no watcher of its own and **must never re-apply a
profile unattended** — `use`/`rollback` are human-confirmed operations.
What is safe to schedule is a read-only *drift notification*: run
`devin-switch doctor` on a timer and surface the result. `doctor`
re-runs the config sanity checks and ranks the closest matching
profile; when external drift appears, the previously active profile
stops matching and the output changes.

A changed `closest profile:` line is your drift signal. Re-applying
stays a deliberate `devin-switch use <profile>` run by you.

Platform setup lives in the OS-specific guides:

- **Linux (systemd user timer):** [drift-check-linux.md](drift-check-linux.md)
- **Windows (Task Scheduler):** [drift-check-windows.md](drift-check-windows.md)
