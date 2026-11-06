# Engineering Guidelines & Agent Rules

This project follows the **Matt Pocock Skills for Real Engineers** engineering discipline framework. All AI agents and pair-programming sessions in this workspace must abide by the conventions described below.

---

## 1. Core Principles

- **No Vibe Coding**: We do not start writing implementation code without an agreed-upon direction, specification, or test plan.
- **Relentless Alignment**: Use `/grill-with-docs` (or `/grill-me`) to resolve ambiguities, challenge assumptions, and agree on boundaries before coding.
- **Domain Modeling**: Build and respect the ubiquitous domain language in [`GLOSSARY.md`](./GLOSSARY.md). Record hard-to-reverse architectural decisions in [`docs/adr/`](./docs/adr/).
- **Deep Modules & Clean Seams**: Design modules that hide complexity behind clean, minimal interfaces. Test through those public interfaces rather than coupling tests to internal implementation details.
- **Test-Driven Development (TDD)**: Work one vertical tracer bullet at a time using the strict Red → Green → Refactor loop (`/tdd`).
- **Two-Axis Code Review**: Verify every non-trivial change along two axes before merging:
  1. *Standards*: Adherence to repository conventions and clean code practices.
  2. *Spec*: Faithful implementation of the originating requirement or ticket without scope creep.
- **Context Hygiene**: Do not let context windows degrade. Clear or compact context between discrete tickets.

---

## 2. Agent skills

### Issue tracker

Issues and specs are tracked via local markdown files under `.scratch/` (with optional GitHub Issues integration via `gh`). See [`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md).

### Triage labels

Canonical roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`docs/agents/triage-labels.md`](./docs/agents/triage-labels.md).

### Domain docs

Single-context repository layout (`GLOSSARY.md` at root and ADRs in `docs/adr/`). See [`docs/agents/domain.md`](./docs/agents/domain.md).

---

## 3. Workflow & Skills Map

When unsure which skill or workflow to use, consult `/ask-matt`.

```
                  ┌──────────────────────┐
                  │  Idea / Requirement  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  /grill-with-docs    │◄─── Updates GLOSSARY.md & docs/adr/
                  └──────────┬───────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼ (Design/UI question?)         ▼ (Clear to plan?)
   ┌───────────────────┐                     │
   │    /prototype     │                     │
   └─────────┬─────────┘                     │
             └───────────────┬───────────────┘
                             ▼
                  ┌──────────────────────┐
                  │       /to-spec       │───► Published to tracker
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     /to-tickets      │───► Tracer bullets with blocking edges
                  └──────────┬───────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼ (Per ticket / Interactive)    ▼ (Orchestrated spec run)
   ┌───────────────────┐           ┌───────────────────┐
   │    /implement     │           │  /implement-spec  │
   └─────────┬─────────┘           └─────────┬─────────┘
             │                               │
             ├───────────────┬───────────────┤
             │               │               │
             ▼               ▼               ▼
      ┌────────────┐  ┌─────────────┐  ┌───────────┐
      │    /tdd    │  │/code-review │  │   /retro  │
      └────────────┘  └─────────────┘  └───────────┘
```

### Key Skills Summary

| Skill | Mode | Purpose |
| :--- | :--- | :--- |
| **`/ask-matt`** | User-invoked | Router to determine which skill or workflow fits your current need. |
| **`/grill-with-docs`** | User-invoked | Sharpens ideas through structured interview; records terms in `GLOSSARY.md` and ADRs. |
| **`/grill-me`** | User-invoked | Stateless interview for non-code designs, specs, or quick alignment. |
| **`/to-spec`** | User-invoked | Synthesizes discussion into an actionable, formal specification. |
| **`/to-tickets`** | User-invoked | Breaks down a spec into vertical slices with explicit blocking dependencies. |
| **`/implement`** | User-invoked | Implements a single ticket cleanly using TDD and code review. |
| **`/implement-spec`**| User-invoked | Coordinates parallel implementer subagents across unblocked tickets on an integration branch. |
| **`/tdd`** | Model-invoked| Strict test-driven development: red → green → refactor. |
| **`/code-review`** | Model-invoked| Two-axis review (Standards + Spec fidelity) on git diff. |
| **`/diagnosing-bugs`**| Model-invoked| Builds a reproducible failing test first before attempting any bug fix. |
| **`/wayfinder`** | User-invoked | Explores huge/foggy architectural efforts via an incremental decision map. |
| **`/improve-codebase-architecture`** | User-invoked | Identifies deep-module and architectural enhancement opportunities. |
| **`/handoff`** | User-invoked | Compacts context into a portable handoff document. |
| **`/retro`** | User-invoked | Suggests environment and standards improvements after a coding session. |
