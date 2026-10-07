# Security Policy

## What this tool does with your data

- **No telemetry.** This project sends nothing to analytics or tracking.
- **Local by default.** Specs and the registry live in local files
  (default registry path in `src/devin_orchestrator/registry.py`;
  overridable via `--registry` and `--spec-file`). No data leaves your
  machine unless you point a command at a remote target.

## Sensitive data handling

- Output intended for sharing must pass through
  [`devin-redact`](https://github.com/Icaro0310/devin-redact) before publication.
- Never commit Devin session databases, `.env` files, tokens, or pairing codes.

## Reporting a vulnerability

Open a **private** security advisory on GitHub, or open an issue marked
`[SECURITY]` **without** including the vulnerable data itself.

Do not file public issues containing secrets, tokens, or session content.
