---
description: Delegate autonomous queue work to the developer or test persona via Agent-tool subagents
argument-hint: "<persona> [<minutes>|until:<iso>] | <persona> <issue>"
---

Orchestrate autonomous Phase-1 work by **delegating to subagents** under `.claude/agents/<persona>.md`. You (the running session) act as orchestrator only: scan the queue, pick the next item, spawn a subagent, receive its summary, decide what's next. The subagent does all the code-writing in its own isolated context.

## Argument parsing

Parse `$ARGUMENTS` as one of:

| Form | Meaning |
|---|---|
| `<persona>` | One pass — pick the highest-priority item and delegate, then stop |
| `<persona> <N>` | Watch mode — work continuously, polling every ~270 s for `<N>` minutes |
| `<persona> until:<iso>` | Watch mode anchored to an absolute deadline (used by self-scheduled wake-ups so the deadline doesn't drift) |
| `<persona> <issue-number>` | One-shot on a specific issue — skip queue scan, delegate immediately |

Valid personas: `developer`, `test`. Anything else: print the line below and stop.

```
Unknown or unsupported persona: "<name>". Valid: developer, test. For firmware, use /firmware (interactive, not autonomous).
```

If the user passes `firmware`: print "Firmware is interactive — use `/firmware` instead." and stop.

On first call with `<minutes>`, compute `end_time = now_utc + <minutes>m` as ISO 8601. Subsequent wake-ups pass `until:<end_time>` to preserve the deadline.

## Step 1 — Confirm the persona file exists

Run `test -f .claude/agents/<persona>.md`. If not present, stop with a clear error. Do not invent a persona.

## Step 2 — Scan the queue (token-efficient)

Skip this step entirely if the argument was a specific issue number.

```bash
gh issue list \
  --repo mak3r/m5stick-encoder \
  --state open \
  --label phase-1 \
  --json number,title,assignees,labels,updatedAt \
  --jq '[.[] | select(([.labels[].name] | index("needs-plan") | not))] | .[] | "#\(.number)  \(.title)  assignees=\([.assignees[].login] | join(",") // "—")  updated=\(.updatedAt[:10])"'
```

```bash
gh pr list \
  --repo mak3r/m5stick-encoder \
  --state open \
  --base main \
  --json number,title,headRefName,reviewDecision,statusCheckRollup,isDraft \
  --jq '.[] | "#\(.number)  \(.title)  branch=\(.headRefName)  review=\(.reviewDecision // "PENDING")  ci=\(if (.statusCheckRollup // [] | length) == 0 then "?" elif (.statusCheckRollup | all(.[]; .state // .conclusion == "SUCCESS")) then "green" else "failing" end)  draft=\(.isDraft)"'
```

Print both query results as compact lines. Do not dump raw JSON to context.

## Step 3 — Pick the highest-priority item

Score order (first match wins; ties broken by oldest `updatedAt`):

| # | Condition |
|---|---|
| 1 | An open PR by this persona with `ci=failing` — fix the breakage |
| 2 | An open PR by this persona with review comments unaddressed — respond |
| 3 | An open issue labeled `phase-1`, no assignees, no open PR on `phase-1/<slug>-<N>` for it, lowest issue number first |
| 4 | An open issue labeled `phase-1` that the persona was previously assigned |

If queue is empty and watch mode active: go to Step 5 to schedule a wake-up. If queue is empty and one-pass mode: print "Queue empty — nothing for `<persona>` to pick up." and stop.

## Step 4 — Delegate to subagent

Spawn one Agent call. Use `subagent_type: <persona>` if your harness has discovered the project's `.claude/agents/<persona>.md`; otherwise use `subagent_type: general-purpose` and include the persona-file path in the prompt so the subagent reads it before acting.

**Prompt template** (substitute the bracketed values):

```
You are the <persona> persona for the m5stick-encoder project at /Users/mark/projects/m5stick-encoder.
Read .claude/agents/<persona>.md FIRST — it defines your toolchain bootstrap, refusal rules, and workflow.

Your task: implement (or, for the test persona, cover with tests) GitHub issue #<N> in mak3r/m5stick-encoder.
Run `gh issue view <N> --repo mak3r/m5stick-encoder` to read it.

Repo state:
- Working directory: /Users/mark/projects/m5stick-encoder
- Default branch: main. PRs target main. Branch protection requires `lint-and-test` CI to pass.
- Use the project venv (.venv/) for all Python tools — global pip/brew/pipx is denied in your sandbox.
- Co-author commits with: Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

Follow your persona's workflow exactly. Do NOT push broken code. If you hit a blocker you can't resolve, post a clear blocker comment on the issue and stop — that's a valid outcome.

When done, return a summary under 150 words including: branch name, commit SHA (verified with `git rev-parse --verify HEAD`), PR URL, tests added, and any open questions for the human.

Do NOT loop to other issues — this is a single delegation.
```

Run the Agent call in the foreground (NOT background) so you can act on the result. Wait for the subagent to return.

## Step 5 — Process the subagent result

The subagent returns one of three outcomes:

- **PR opened with green CI** — log it (one-line print) and proceed to Step 6
- **Blocker posted on issue (no PR)** — log the blocker reason; do not retry the same issue. Proceed to Step 6 (which will skip this issue next scan because the assignee/comment marks it as touched)
- **Anything else (crash, ambiguous result)** — print the subagent's full return to the user and stop, even if watch mode is on. Don't loop into uncertainty.

After a successful PR open, if you are mak3r and the PR's CI is green, you MAY merge it via `gh pr merge <N> --squash --delete-branch` — but only if the PR has no draft flag, no review comments awaiting reply, and CI is green. Otherwise leave it for human review.

## Step 6 — Loop or schedule

Single-pass mode (no minutes/deadline): print a one-line summary (`Completed <N> item(s) for <persona>.`) and stop.

Watch mode:
- `now_utc < end_time` and Step 5 just completed an item: immediately return to Step 2.
- `now_utc < end_time` and queue was empty: call `ScheduleWakeup` with `delaySeconds: 270`, `reason: "Poll for new <persona> work"`, `prompt: "/watch-work <persona> until:<end_time_iso>"`. Then stop this turn (the wake-up will resume).
- `now_utc >= end_time`: print `Session complete for <persona>. Items handled this session: <N>.` and stop.

## Token-efficiency rules

1. `--json <fields>` + `--jq` on every gh call — never dump raw JSON.
2. Don't fetch issue bodies in the orchestrator; let the subagent do that.
3. Never read the same source file in the orchestrator that the subagent will read.
4. If the subagent's summary mentions "see the file at path X," DO NOT read X here — accept the summary unless something is concretely wrong.

## What you (orchestrator) refuse to do

- Modify any file under `src/`, `tests/`, `.claude/agents/`, `LICENSE`. That's subagent territory or human territory.
- Skip the queue scan in one-pass mode unless an issue number was given explicitly.
- Continue past a subagent crash without surfacing it to the human.
- Auto-merge any PR with `needs-plan` label, or any PR for a phase-2-or-later issue.
