# ForNeWord Behavioral Rules

A comprehensive behavioral rule system for Claude Code, covering anti-stall, completion verification, simplicity, surgical changes, and 98+ documented failure mode patterns.

Use `/cc-rules` to load all rules into the current session.

## Quick Start

```bash
# Install the plugin
/plugin marketplace add forever-218/cc-rules
/plugin install cc-forever-rules@cc-rules

# Load rules in any session
/cc-rules
```

## What's Included

### Skills
- **cc-rules**: 98+ behavioral rules — anti-stall, completion verification, simplicity, surgical changes
- **reasoning-tool-selector** (v1.2.0): Generic MCP coordination pipeline — self-critique, reasoning tool selection, API doc discipline

### Hooks
- **pre_tool_use.py**: Read-before-write enforcement, blast-radius checks, destructive command guard, Godot play-state detection
- **post_tool_use.py**: Read-cache tracking, GDScript syntax validation, code-modification tracking, repeat-error detection
- **stop_hook.py**: Gatekeeper engine — agent FAIL output scanning, test verification loop, clarify-before-act detection, behavioral blocking rules
- **session_start.py**: Mandatory pipeline injection before model starts thinking

### Guard Agents
4 stop-hook agents for automated review:
- **代码审查**: Bug detection, test coverage, dependency check, simplicity audit
- **任务追踪**: Completion audit, scope creep detection, memory save suggestions
- **正确性**: Regression prevention, design respect, upstream>downstream enforcement
- **行为审查**: Disagree-when-wrong, assumption surfacing, anti-rationalization, fail-explicitly
