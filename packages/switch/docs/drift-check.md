# Scheduled drift check (notification only)

`devin-switch` has no watcher of its own and **must never re-apply a
profile unattended** — `use`/`rollback` are human-confirmed operations.
What is safe to schedule is a read-only *drift notification*: run
`devin-switch doctor` on a timer and surface the result. `doctor`
re-runs the config sanity checks and ranks the closest matching
profile; when external drift appears, the previously active profile
stops matching and the output changes.

## systemd (Linux)

```ini
# ~/.config/systemd/user/devin-switch-drift.service
[Unit]
Description=devin-switch drift check (notification only)

[Service]
Type=oneshot
ExecStart=devin-switch doctor --json
SyslogIdentifier=devin-switch-drift
```

```ini
# ~/.config/systemd/user/devin-switch-drift.timer
[Unit]
Description=hourly devin-switch drift check

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now devin-switch-drift.timer
journalctl --user -u devin-switch-drift -f
```

A changed `closest profile:` line in the journal is your drift signal.
Re-applying stays a deliberate `devin-switch use <profile>` run by you.

## Task Scheduler (Windows)

```powershell
schtasks /create /tn DevinSwitchDrift /sc hourly `
  /tr "devin-switch doctor --json >> %USERPROFILE%\.devin\switch-drift.log 2>&1"
```

The log tail is the notification channel — same rule: notify, never
apply.
