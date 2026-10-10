# Running devin-bridge as a service

`devin-bridge` is designed for long-running operation — it is a policy
frontier (allow/deny/ask, fail-closed) whose mailbox intake and ACP
sessions only make sense while it stays up. Below is the formalization
of the pattern that is already expected.

## systemd (Linux)

```ini
# ~/.config/systemd/user/devin-bridge.service
[Unit]
Description=devin-bridge ACP policy frontier
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/env node %h/devin/devin-ecosystem/devin-control/packages/bridge/bin/devin-bridge.js --policy %h/.devin/bridge-policy.json
Restart=on-failure
RestartSec=5
# The bridge is fail-closed by design: on crash, intakes deny rather
# than pass. Restart=on-failure restores the frontier; nothing is
# auto-approved while it is down.

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now devin-bridge.service
journalctl --user -u devin-bridge -f
```

## Task Scheduler (Windows)

```powershell
schtasks /create /tn DevinBridge /sc onlogon `
  /tr "node %USERPROFILE%\devin\devin-ecosystem\devin-control\packages\bridge\bin\devin-bridge.js --policy %USERPROFILE%\.devin\bridge-policy.json"
```

## Notes

- Policy changes are deliberate edits to the policy file followed by a
  service restart — never runtime mutation through an agent surface.
- The `read-only` preset (observe-only intake) is the right profile for
  unattended operation; interactive `ask` prompts need a human present.
