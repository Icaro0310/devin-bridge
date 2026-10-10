# devin-switch drift check — systemd user timer (Linux)

`doctor` prints a human-readable report (there is no `--json` flag); the
journal is the notification channel.

```ini
# ~/.config/systemd/user/devin-switch-drift.service
[Unit]
Description=devin-switch drift check (notification only)

[Service]
Type=oneshot
ExecStart=devin-switch doctor
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
