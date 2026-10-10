# Running devin-office as a service

`devin-office` is a local, read-only dashboard: `daemon.py` polls
`sessions.db` and serves `WorldState` at `/api/state` plus `index.html`
(stdlib only, zero dependencies). Running it as a user service just
formalizes the pattern it already follows.

## systemd (Linux)

```ini
# ~/.config/systemd/user/devin-office.service
[Unit]
Description=devin-office local dashboard (read-only sessions.db)
After=default.target

[Service]
Type=simple
WorkingDirectory=%h/devin/devin-ecosystem/devin-control/packages/office
ExecStart=/usr/bin/env python3 %h/devin/devin-ecosystem/devin-control/packages/office/daemon.py --port 8788
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now devin-office.service
# dashboard at http://localhost:8788
```

The service is bound to localhost and only ever reads the store —
there is no mutation path to guard, which is why serving it unattended
is safe.
