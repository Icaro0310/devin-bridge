# devin-office dashboard — Task Scheduler (Windows)

The dashboard is a persistent HTTP server; a logon task keeps it up.

```powershell
schtasks /create /tn DevinOffice /sc onlogon `
  /tr "cmd /c cd /d %USERPROFILE%\devin\devin-ecosystem\devin-control\packages\office && python daemon.py --port 8788"
```

Bound to localhost; dashboard at http://localhost:8788. Writes are
limited to `kanban.json` marks via `POST /api/kanban`.
