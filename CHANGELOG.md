# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-03

### Added

- Initial public release of Devin Office, a local-first dashboard of active
  Devin CLI/Desktop sessions and subagents rendered as an SVG circuit view.
- `daemon.py`: standalone read-only mode; reads the local `sessions.db` and
  serves `/api/state` plus the dashboard on loopback, Python stdlib only.
- `probe.py` + `hub.py`: optional split mode; the probe polls local state
  and posts changes to a private hub that serves the dashboard.
- `executor.py`: optional ACP control process for message/spawn/kill
  requests; disabled by default and gated behind explicit opt-in.
- `index.html`: self-contained SVG dashboard (Devin chip with live traces
  to tools and subagent arms); no JavaScript/CSS build step.
- Cross-platform Devin store detection (Windows `%APPDATA%`, Linux XDG,
  macOS), loopback-restricted CORS, and token requirements for
  non-loopback hub binds.
- EN/PT-BR READMEs, tests workflow, preview screenshot and live demo page.
