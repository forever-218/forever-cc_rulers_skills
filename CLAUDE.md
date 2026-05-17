# ForNeWord Behavioral Rules

A comprehensive behavioral rule system for Claude Code, covering anti-stall, completion verification, simplicity, surgical changes, and 98+ documented failure mode patterns.

Use `/cc-rules` to load all rules into the current session.

## Quick Start

```bash
# Install the plugin
/plugin marketplace add YOUR_GITHUB_USERNAME/cc-rules
/plugin install cc-rules@cc-rules

# Load rules in any session
/cc-rules
```

## What's Included

- **Anti-Stall**: Prevents 30min+ zero-output thinking, convergence detection, error retry limits
- **Completion Verification**: Audit all requirements before declaring done, verify after changes
- **Simplicity First**: No speculative code, no over-engineering, rewrite when bloated
- **Surgical Changes**: Touch only what you must, clean up your own mess
- **Execution Rules**: Direct execution, exhaustive enumeration, clarify ambiguity, prioritize by impact
- **Detailed Patterns**: 38 interaction failures, 41 premature-exit modes, 19 unattended stall modes
