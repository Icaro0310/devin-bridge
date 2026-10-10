# devin-bridge intake — Task Scheduler (Windows)

Same one-shot model as the Linux timer: a scheduled task runs
`devin-bridge intake`, which drains the mailbox inbox and exits.

```powershell
schtasks /create /tn DevinBridgeIntake /sc minute /mo 5 `
  /tr "cmd /c node %USERPROFILE%\devin\devin-ecosystem\devin-control\packages\bridge\bin\devin-bridge.js intake --policy %USERPROFILE%\.devin\bridge-policy.json >> %USERPROFILE%\.devin\bridge-intake.log 2>&1"
```

Each run appends the JSON `{mailbox, results}` report to
`%USERPROFILE%\.devin\bridge-intake.log` — Task Scheduler does not
retain a scheduled command's stdout, hence the `cmd /c` wrapper. Check
`failed` entries there and their `.err` files under the mailbox to spot
rejected or errored tasks.
