# ForNeWord Behavioral Rules

A behavioral rule system for Claude Code that prevents common AI coding failures — derived from systematic analysis of real interaction patterns, not theoretical assumptions.

## Principles

| Principle | What It Prevents |
|---|---|
| **Anti-Stall** | 30min+ zero-output thinking, decision loops, error retry spirals |
| **Completion Verification** | Incomplete work, false "done", untested changes |
| **Simplicity First** | Over-engineering, speculative abstractions, needless flexibility |
| **Surgical Changes** | Unrelated code damage, style inconsistency, orphaned imports |
| **Execution Rules** | Lazy enumeration, telling instead of doing, unclear communication |

## Installation

```bash
/plugin marketplace add YOUR_GITHUB_USERNAME/cc-rules
/plugin install cc-rules@cc-rules
```

Then in any session:
```
/cc-rules
```

## Project Integration

To auto-load rules for a specific project without invoking the skill, copy the rules from `CLAUDE.md` into your project's `CLAUDE.md`.

## Also See

- `load_rules.sh` — Standalone script to inject rules into any session. Run `bash load_rules.sh` from any CC window.
- `CLAUDE.md` in this repo — Merged rules from Karpathy Guidelines + ForNeWord custom patterns.
- CC auto-memory at `<project>/.claude/.../memory/` — Full pattern catalogs (98+ documented modes).

## License

MIT
