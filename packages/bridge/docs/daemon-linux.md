# devin-bridge intake — systemd user timer (Linux)

A `oneshot` service drains the mailbox inbox; a timer re-runs it
periodically. `Type=oneshot` is correct here: the CLI exits after each
batch, so `Restart=` has nothing to hold up — the timer provides the
recurrence instead.

```ini
# ~/.config/systemd/user/devin-bridge-intake.service
[Unit]
Description=devin-bridge mailbox intake (one-shot)

[Service]
Type=oneshot
ExecStart=/usr/bin/env node %h/devin/devin-ecosystem/devin-control/packages/bridge/bin/devin-bridge.js intake --policy %h/.devin/bridge-policy.json
```

```ini
# ~/.config/systemd/user/devin-bridge-intake.timer
[Unit]
Description=periodic devin-bridge mailbox intake

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now devin-bridge-intake.timer
journalctl --user -u devin-bridge-intake.service -f
```

Each run prints a JSON `{mailbox, results}` report to the journal —
`failed` entries land next to their `.err` files in the mailbox.
