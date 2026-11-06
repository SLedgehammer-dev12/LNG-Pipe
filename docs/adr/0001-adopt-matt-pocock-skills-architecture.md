# 0001: Adopt Matt Pocock Skills & Engineering Discipline Framework

We adopt the engineering skills framework from `mattpocock/skills` to govern software design, specifications, testing, and implementation.

## Context

AI agent assisted coding frequently suffers from "vibe coding", lack of alignment between developer intent and implementation, premature coding without clear specs, lack of test-driven feedback loops, and unbounded context windows that degrade reasoning.

## Decision

We incorporate Matt Pocock's skills framework directly into this repository:

1. **Alignment First**: Before jumping into implementation, use `/grill-with-docs` or `/grill-me` to clarify requirements, define domain language in `GLOSSARY.md`, and record architectural choices in `docs/adr/`.
2. **Spec & Decomposition**: Decompose complex features into `/to-spec` and tracer-bullet `/to-tickets` with explicit blocking dependencies.
3. **Execution**: Implement slices using strict test-driven development (`/tdd`) and review against code standards and original specs via `/code-review`.
4. **Context Hygiene**: Keep context windows fresh between tickets and work in discrete, verifiable units.

## Consequences

- Faster alignment, less rework, clear paper trail of design decisions.
- Predictable, robust test coverage via TDD red-green-refactor loops.
