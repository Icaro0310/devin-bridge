# devin-office dashboard — systemd user service (Linux)

The dashboard is a persistent HTTP server, so `Type=simple` with
`Restart=on-failure` is the right shape (unlike the one-shot tools in
the sibling packages).

```ini
# ~/.config/systemd/user/devin-office.service
[Unit]
Description=devin-office local dashboard (reads sessions.db; kanban marks only)
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

Bound to localhost by default. Writes are limited to `kanban.json`
marks via `POST /api/kanban` — `sessions.db` is only ever read.
