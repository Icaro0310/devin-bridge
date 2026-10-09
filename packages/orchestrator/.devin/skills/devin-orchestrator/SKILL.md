---
name: devin-orchestrator
description: "Assess delegation at every session start and coordinate bounded Devin background subagents, collect results, and preserve repo/session safety."
triggers: [model, user]
---

# Devin Orchestrator — bounded background workers by default

This orchestrator runs **inline in the main Devin session**. Do not run this skill as a subagent or delegate the orchestrator itself. Its job is to assess delegation, coordinate any useful workers, and return one integrated result from the main session. The main session is the **Boss**: it decomposes, dispatches, collects and reports — workers never talk to the user.

## Devin-specific contract

Use Devin's documented project skill and rule formats, not assumptions from another agent product:

- Project skill: `.devin/skills/<name>/SKILL.md`; this skill is invoked by the user or model through `triggers: [model, user]`.
- An always-on project rule is a Markdown file under `.devin/rules/` with `trigger: always_on`.
- Devin background subagents let the parent continue working. Background workers inherit only already-approved tools; an unapproved tool is denied rather than prompting from the background worker.
- Use Devin's documented subagent controls and profiles. `subagent_explore` is read-only for research; `subagent_general` can implement bounded code changes. Do not assume hidden APIs or undocumented quotas.

The official docs describe background execution but do not promise a hard CPU or concurrency quota. The limits below are **local operating policy** that the parent must track, not platform-enforced guarantees. Skill-as-subagent execution is deliberately not used here.

## 1. Assess delegation in every new session

At the start of every new session, make an explicit internal decision about whether delegation would help; reassess if the scope materially changes. The assessment is mandatory, but spawning is not.

- **Stay inline** for trivial questions, one-step edits, tightly coupled or dependent work, sensitive operations, ambiguous requests, or work where setup/coordination would cost more than it saves. Never spawn for a trivial request.
- **Delegate** when work is substantive, independently useful, bounded, and can progress without the parent's missing conversation context. Prefer a background worker so the main session remains responsive and the user can keep writing instead of waiting in a queue.
- If background subagents are unavailable or a task needs interactive permission, continue inline or use a foreground worker only when that is the safe, useful option; do not pretend a background task was launched.

## 2. Plan before dispatch (code, not opinion)

Before launching workers for a multi-unit task, generate the plan with the deterministic planner:

```bash
devin-orchestrator plan '{"kind":"implementation","independent_units":3,"needs_write":true,"estimated_scope":"large","summary":"API + UI + tests"}'
```

`src/devin_orchestrator/planner.py` takes a spec JSON with structured signals (`kind`, `independent_units`, `estimated_scope`, `needs_write`) and returns `{workers, mode, profiles, collect, warnings}`. The model decides *how* to decompose; the bounds are enforced by code — do not try to bypass them. `collect=true` in the plan is a contract: never report done without collecting results.

## 3. Enforce local worker and CPU bounds

- Default to **1 active worker**. Use more only when tasks are genuinely independent and the extra concurrency is worth the context and compute cost.
- Never exceed **3 concurrent workers** (active subagents; the main session is the coordinator, not a worker, and completed workers no longer count). Check active status before every launch; do not rely on Devin to enforce this local cap. `DEVIN_MAX_WORKERS` can only lower this bound, never raise it.
- Do not spawn nested workers. Put an explicit "do not spawn children" instruction in every delegated task. The planner returns 0 workers when `DEVIN_INSIDE_SUBAGENT=1`.
- Keep CPU-heavy tests, builds, compiles, benchmarks, indexing, and end-to-end suites serialized: run no more than one such job at a time. Do not launch multiple test workers against the same machine or repository.
- Avoid delegating heavy test runs. If one is necessary, assign at most one worker and wait for it to finish before starting another CPU-heavy job.

## 4. Choose the narrowest worker profile

- Use a read-only `subagent_explore` worker for research, codebase discovery, documentation checks, audits, and test-result analysis (`needs_write=false`). Ask for file paths, evidence, uncertainty, and sources; do not grant write work for research.
- Use a write-capable `subagent_general` worker only for a substantive, isolated implementation with a precise file/task boundary. Confirm the working tree first, assign non-overlapping files, and keep integration and final verification with the parent.
- Do not send secrets, credentials, full session transcripts, or unrelated private context. Give each worker only the context needed for its bounded task. Workers are stateless — front-load complete, self-contained prompts.

## 5. Reuse the exact repository session

Before repo-specific work, resolve the canonical repository root and consult the configured `.sessions.json` repository-session index (in this ecosystem, the index is at the `devin-ecosystem` root). Match both the repository entry and its canonical `cwd`.

- If there is one exact mapping, resume its recorded Devin session and continue there; never create another session or duplicate.
- Never guess a session from a similar title, silently issue a new-session request, add a duplicate mapping, or create a second repo session.
- If the index or exact mapping is absent, malformed, mismatched, or ambiguous, stop and ask the user before creating a session.
- Treat `.sessions.json` as a mapping only. Do not read or write any live Devin session database or session store as part of orchestration.

## 6. Delegate bounded tasks and keep the parent moving

Each worker request should state: one objective; relevant context and exact repository root; read-only versus write permission; allowed files; what not to touch; no nested workers; expected evidence; and a concise result format (findings, paths changed, commands/tests, outcome, risks/blockers).

Launch useful independent work in the background first (`run_subagent(is_background=true)`). While it runs, continue unrelated, low-CPU parent work — **never poll in a blocking loop**. Avoid overlapping edits and do not have multiple workers own the same files. For an existing repo, session reuse applies before assigning any repo-specific worker task.

## 7. Collect, verify, and aggregate every result

- Track each worker's ID, task, profile, status, and owned files in the parent session.
- After a background worker finishes, read its full result using Devin's documented result view (for CLI, `read_subagent`; in Desktop, the subagent panel). A completion notification is not the deliverable.
- Collect every delegated result and resolve conflicts against source evidence. Inspect changed paths and run the agreed lightweight verification in the parent session. Do not claim unverified tests passed.
- Do not end the turn with delegated work still running or results unread. If a worker fails or a background permission is denied, report the blocker and continue safely; do not silently broaden permissions.
- The main session owns synthesis and the final report: key findings, worker outcomes, files changed, exact test results, and unresolved risks.

## 8. Protect the working tree and gate publication

- Inspect `git status --short` and the relevant diff before a write-capable task. Preserve pre-existing dirty and untracked files; workers may change only their assigned paths.
- Never use broad staging such as `git add .` or `git add -A`. Stage exact paths only when explicitly requested.
- A local draft is not permission to publish. Creating a hosted repository, adding/changing a remote, committing, pushing, or releasing is allowed only after tests pass **and** the user explicitly requests that specific action. If either condition is missing, stop at the local draft and ask.
- Keep evals deterministic and lightweight (`evals/evals.json` fixtures). Do not run a model-heavy eval loop unless the user explicitly asks and separately authorizes its resource use.

## Official Devin references

- [Devin CLI skills](https://docs.devin.ai/cli/extensibility/skills/overview)
- [Devin CLI rules](https://docs.devin.ai/cli/extensibility/rules)
- [Devin CLI subagents](https://docs.devin.ai/cli/subagents)
- [Devin Local / Desktop agent](https://docs.devin.ai/desktop/devin-local)
