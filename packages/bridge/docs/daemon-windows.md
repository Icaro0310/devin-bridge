# devin-bridge intake — Task Scheduler (Windows)

Same one-shot model as the Linux timer: a scheduled task runs
`devin-bridge intake`, which drains the mailbox inbox and exits.

```powershell
schtasks /create /tn DevinBridgeIntake /sc minute /mo 5 `
  /tr "node %USERPROFILE%\devin\devin-ecosystem\devin-control\packages\bridge\bin\devin-bridge.js intake --policy %USERPROFILE%\.devin\bridge-policy.json"
```

Each run emits the JSON `{mailbox, results}` report on stdout; check
`failed` entries and their `.err` files under the mailbox to spot
rejected or errored tasks.
