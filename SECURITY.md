# Security Policy

## What this tool does with your data

- **No telemetry.** This project sends nothing to analytics or tracking.
- **Local by default; hubs on demand.** In split mode, `probe.py` sends
  session metadata and tool activity to the hubs you configure — that is
  its function. Without configured hubs, processing stays local.
- **Generated files.** The tool writes operational files such as
  `up.log` and executor state; they live alongside the project and are
  never uploaded.

## Sensitive data handling

- Output intended for sharing must pass through
  [`devin-redact`](https://github.com/Icaro0310/devin-redact) before publication.
- Never commit Devin session databases, `.env` files, tokens, or pairing codes.

## Reporting a vulnerability

Open a **private** security advisory on GitHub, or open an issue marked
`[SECURITY]` **without** including the vulnerable data itself.

Do not file public issues containing secrets, tokens, or session content.
