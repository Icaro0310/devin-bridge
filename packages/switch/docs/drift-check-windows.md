# devin-switch drift check — Task Scheduler (Windows)

`doctor` prints a human-readable report (there is no `--json` flag);
the log tail is the notification channel — same rule: notify, never
apply.

```powershell
schtasks /create /tn DevinSwitchDrift /sc hourly `
  /tr "devin-switch doctor >> %USERPROFILE%\.devin\switch-drift.log 2>&1"
```
