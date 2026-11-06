# Issue tracker

Issues and specs for this repo can live as **Local Markdown files** (default) or as **GitHub Issues** via `gh`.

---

## 1. Local Markdown (Default for local & offline development)

Issues live as markdown files under `.scratch/<feature-slug>/`.

### Conventions

- **Feature directory**: `.scratch/<feature-slug>/`
- **Spec location**: `.scratch/<feature-slug>/spec.md`
- **Tickets**: One file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered starting from `01`. Never a single combined tickets file.
- **Triage state**: Recorded as a `Status:` line near the top of each ticket file (e.g. `Status: ready-for-agent`, `Status: claimed`, `Status: resolved`).
- **Dependencies**: A `Blocked by: NN, NN` line near the top of the ticket. A ticket is unblocked when every ticket it lists has `Status: resolved`.
- **Comments & History**: Appended to the bottom under `## Comments`.

### Wayfinding Operations (used by `/wayfinder`)
- **Map**: `.scratch/<effort>/map.md` (holds Notes, Decisions-so-far, Fog).
- **Child tickets**: `.scratch/<effort>/issues/NN-<slug>.md`.
- **Claim**: Set `Status: claimed` before beginning implementation.
- **Resolve**: Append solution under `## Answer`, set `Status: resolved`, and link into `map.md`.

---

## 2. GitHub Issues (When connected to a GitHub remote)

When a `git remote` pointing to GitHub is configured and the user chooses GitHub tracking:

### Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments`
- **Sub-issues / Hierarchy**: `gh issue create --parent <parent> ...` or add `Part of #<parent>` to body.
- **Blocking**: Native dependencies with `gh issue edit <child> --add-blocked-by <blocker>` or `Blocked by: #<n>`.
- **Labels**: `gh issue edit <number> --add-label "..."`
- **Close**: `gh issue comment <number> --body "..."` followed by `gh issue close <number>`.
