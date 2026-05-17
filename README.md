# cc-forever-rules

A behavioral rule system for Claude Code that prevents common AI coding failures — derived from systematic analysis of real interaction patterns, not theoretical assumptions.

## Principles

| Principle | What It Prevents |
|---|---|
| **Anti-Stall** | 30min+ zero-output thinking, decision loops, error retry spirals |
| **Completion Verification** | Incomplete work, false "done", untested changes |
| **Simplicity & Surgical Changes** | Over-engineering, speculative abstractions, unrelated code damage, orphaned imports |
| **Interaction Quality** | Wrong-direction execution, symptom fixing, misreading urgency, missing context |
| **Execution Rules** | Lazy enumeration, telling instead of doing, unclear communication |

## Installation

```bash
/plugin marketplace add forever-218/cc-rules
/plugin install cc-forever-rules@cc-rules
```

Then in any session:
```
/cc-rules
```

## Project Integration

To auto-load rules for a specific project without invoking the skill, copy the rules from `CLAUDE.md` into your project's `CLAUDE.md`.

## Also See

- `load_rules.sh` — Standalone script to inject rules into any session. Run `bash load_rules.sh` from any CC window.
- `CLAUDE.md` in this repo — Quick reference for project-scope installs.
- `README.zh.md` — 中文版文档.

## License

MIT
