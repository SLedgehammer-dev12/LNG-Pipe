# Engineering Guidelines & Agent Rules

This project unifies the **Matt Pocock Skills for Real Engineers** engineering discipline framework with the specialized engineering subagents and **Ponytail Lazy Senior Developer** practices from `Heat_Exchanger_Calc`.

All AI agents in both **Antigravity** and **OpenCode** must abide by the conventions described below.

---

## 1. Core Principles

- **No Vibe Coding**: We do not write implementation code without an agreed-upon direction, specification, or test plan.
- **Relentless Alignment**: Use `/grill-with-docs` (or `/grill-me`) to resolve ambiguities, challenge assumptions, and agree on boundaries before coding.
- **Domain Modeling**: Build and respect the ubiquitous domain language in [`GLOSSARY.md`](./GLOSSARY.md). Record hard-to-reverse architectural decisions in [`docs/adr/`](./docs/adr/).
- **Deep Modules & Clean Seams**: Design modules that hide complexity behind clean, minimal interfaces. Test through those public interfaces rather than coupling tests to internal implementation details.
- **Test-Driven Development (TDD)**: Work one vertical tracer bullet at a time using the strict Red → Green → Refactor loop (`/tdd`).
- **Ponytail Lazy Senior Dev Discipline**:
  - The best code is the code never written. Solve the whole problem with the least new code.
  - Standard library and installed dependencies first. No useless wrappers, over-abstractions, or "for later" code.
  - End responses with what was skipped, what was not checked, and any risk the user must know.
- **Two-Axis Code Review**: Verify every non-trivial change along two axes before merging:
  1. *Standards*: Adherence to repository conventions, Fowler smells, and lean code practices (`/ponytail-review` / `/code-review`).
  2. *Spec*: Faithful implementation of the originating requirement or ticket without scope creep.
- **Context Hygiene**: Clear or compact context between discrete tickets.

---

## 2. Specialized Engineering Subagents

The workspace includes specialized domain agents ready for both Antigravity and OpenCode:

| Agent | Scope & Domain Expertise |
| :--- | :--- |
| **`senior-mechanical-engineer`** | ASME Section VIII Div 1 pressure vessels (UG-27 shell thickness, UG-32/34 heads, UG-99 hydrotest), TEMA Class R/C/B standards (tubesheets, baffle spacing, $\rho v^2$ impingement), API 661 air-cooled heat exchangers, and Flow-Induced Vibration (FIV) analysis. |
| **`senior-thermodynamic-engineer`** | Industrial heat exchanger sizing, Organic Rankine Cycle (ORC) power loops, multi-WHRU networks, LMTD Bowman factor, $\varepsilon$-NTU solvers, CoolProp Helmholtz EOS real fluids, and hydraulic loops. |
| **`senior-tester`** | QA and test engineering: First/Second Law thermodynamic invariants, floating-point stability, boundary degeneracy ($m \to 0$, $UA \to 0$), property-based testing (Hypothesis), 100+ scenario verification matrices, and automated regression suites. |
| **`ponytail`** | Lazy senior developer mode. Solves tasks with the smallest complete change, stdlib first, YAGNI, and rigorous verification. |
| **`ponytail-reviewer`** | Senior code reviewer evaluating diffs like an on-call engineer paged at 2am: correctness, security, real load, test coverage, speed, and lean code. |
| **`ponytail-auditor`** | Whole-repo architectural auditor inspecting whole-codebase bugs, security vulnerabilities, scaling bottlenecks, dead code, and bloat. |

---

## 3. Agent Configuration & Environment Compatibility

This workspace is simultaneously configured for:

1. **Google Antigravity**:
   - Agent definitions: [`.agents/agents/`](./.agents/agents/)
   - Rules: [`.agents/rules/ponytail.md`](./.agents/rules/ponytail.md)
   - Skills: [`.agents/skills/`](./.agents/skills/)
   - Domain docs: [`GLOSSARY.md`](./GLOSSARY.md) and [`docs/adr/`](./docs/adr/)
   - Issue tracker: [`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md)

2. **OpenCode**:
   - Master configuration: [`opencode.json`](./opencode.json)
   - Agent definitions: [`.opencode/agents/`](./.opencode/agents/)
   - Slash commands: [`.opencode/command/`](./.opencode/command/)
   - Plugins: [`.opencode/plugins/`](./.opencode/plugins/)

---

## 4. Agent Skills

### Issue Tracker
Issues and specs are tracked via local markdown files under `.scratch/` (with optional GitHub Issues integration via `gh`). See [`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md).

### Triage Labels
Canonical roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`docs/agents/triage-labels.md`](./docs/agents/triage-labels.md).

### Domain Docs
Single-context repository layout (`GLOSSARY.md` at root and ADRs in `docs/adr/`). See [`docs/agents/domain.md`](./docs/agents/domain.md).

---

## 5. Workflow & Skills Map

When unsure which skill or workflow to use, consult `/ask-matt` or run `/ponytail-help`.

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
             ▼ (Design/UI/3D question?)      ▼ (Clear to plan?)
   ┌───────────────────────────┐             │
   │ /prototype OR /teardown   │             │
   └─────────────┬─────────────┘             │
                 └───────────┬───────────────┘
                             ▼
                  ┌──────────────────────┐
                  │       /to-spec       │───► Published to tracker (.scratch/)
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
      │ (Red-Green)│  │ /ponytail-  │  │           │
      │            │  │   review    │  │           │
      └────────────┘  └─────────────┘  └───────────┘
```

### Complete Skills Reference

#### Engineering Discipline
- **`/ask-matt`**: Router to determine which skill or workflow fits your situation.
- **`/grill-with-docs`**: Sharpens ideas through structured interview; records terms in `GLOSSARY.md` and ADRs.
- **`/to-spec`**: Synthesizes discussion into an actionable, formal specification.
- **`/to-tickets`**: Breaks down a spec into vertical slices with explicit blocking dependencies.
- **`/implement`**: Implements a single ticket cleanly using TDD and code review.
- **`/implement-spec`**: Coordinates parallel implementer subagents across unblocked tickets on an integration branch.
- **`/tdd`**: Strict test-driven development: red → green → refactor.
- **`/code-review`**: Two-axis review (Standards + Spec fidelity) on git diff.
- **`/diagnosing-bugs`**: Builds a reproducible failing test first before attempting any bug fix.
- **`/wayfinder`**: Explores huge/foggy architectural efforts via an incremental decision map.
- **`/improve-codebase-architecture`**: Identifies deep-module and architectural enhancement opportunities.
- **`/retro`**: Suggests environment and standards improvements after a coding session.

#### Specialized Thermal, Mechanical & Testing Skills
- **`/senior-mechanical-engineer`**: ASME Section VIII UG-27, TEMA Class R/C/B, API 661, tubesheet stress, and FIV vibration checks.
- **`/senior-thermodynamic-engineer`**: Heat exchanger thermal sizing, ORC cycles, WHRU networks, LMTD/$\varepsilon$-NTU, and fluid property verification.
- **`/senior-tester`**: Physical invariant testing, Hypothesis property-based testing, floating point stability, and regression suites.

#### Ponytail Lazy Senior Developer
- **`/ponytail`**: Smallest complete change, stdlib first, YAGNI, and self-checks.
- **`/ponytail-review`**: Independent review along correctness, security, load, tests, speed, and lean code.
- **`/ponytail-audit`**: Whole-codebase architecture, bugs, security, scaling, and dead code audit.
- **`/ponytail-debt`**: Debt ledger of all shortcuts taken.
- **`/ponytail-gain`**: Measured savings (code, cost, speed).
- **`/ponytail-help`**: Quick reference for ponytail commands.

#### Architecture, 3D Visualization & Indexing
- **`/repository-indexer`**: Scans the codebase and updates `PROJECT_INDEX.md` and `PROJECT_INDEX.json`.
- **`/teardown`**: Generates interactive 3D mechanisms / simulators with Three.js that users can explode and inspect.
- **`/prototype`**: Quick throwaway logic or UI prototypes to validate questions before building.
