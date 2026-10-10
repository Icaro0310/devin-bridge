# Running devin-bridge intake on a schedule

`devin-bridge` is a one-shot command-line program, not a persistent
daemon: `devin-bridge intake` drains every file currently in the mailbox
inbox and exits. Unattended operation therefore means **scheduling
periodic intakes**, not keeping a process alive — the fail-closed
policy frontier is enforced inside each run, so a crashed or absent
schedule simply leaves tasks unprocessed rather than auto-approved.

Platform setup lives in the OS-specific guides:

- **Linux (systemd user timer):** [daemon-linux.md](daemon-linux.md)
- **Windows (Task Scheduler):** [daemon-windows.md](daemon-windows.md)

## Notes

- Policy changes are deliberate edits to the policy file — they take
  effect on the next scheduled intake, never through runtime mutation.
- The `read-only` preset (observe-only intake) is the right profile for
  unattended operation; interactive `ask` prompts need a human present.
