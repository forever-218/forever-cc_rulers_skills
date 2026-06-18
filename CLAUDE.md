# cc-forever-rules

A comprehensive behavioral enforcement system for Claude Code. Combines declarative rules with **mechanical hooks** that physically block the model from taking shortcuts — it's not just "please remember," it's "you CANNOT proceed without doing this."

## Quick Start

```bash
/plugin marketplace add forever-218/cc-rules
/plugin install cc-forever-rules@cc-rules
/cc-rules
```

## Architecture

```
User message
    │
    ▼
SessionStart Hook  →  injects mandatory pipeline into system prompt
    │
    ▼
PreToolUse Hook  →  blocks invalid tool calls BEFORE execution
    │
    ▼
Model responds (with Skill checks, reasoning, MCP tools)
    │
    ▼
PostToolUse Hook  →  verifies writes, validates syntax/structure
    │
    ▼
Stop Hook  →  gatekeeper: mechanical build, reconciliation, quality checks
    │           exit 0 = done, exit 2 = rewake model to fix issues
    ▼
4 Guard Agents  →  LLM-level review (code, task, correctness, behavior)
```

## Skills

| Skill | Purpose |
|-------|---------|
| **cc-rules** | 98+ behavioral rules — anti-stall, completion verification, simplicity, surgical changes |
| **reasoning-tool-selector** | MCP coordination pipeline — self-critique, reasoning tool selection, API doc discipline |

## Hooks

### 1. PreToolUse Hook (`pre_tool_use.py`)

Intercepts tool calls BEFORE execution. Can block (exit 2) or warn.

| Guard | What it does | Type |
|-------|-------------|------|
| **Reasoning tracker** | Records when deep-thinker/sequential-thinking/yggdrasil is used | State |
| **Reasoning-before-edit** | Blocks Edit/Write/Bash unless reasoning tool was used this turn | 🛑 Block |
| **Read-before-write** | Blocks Edit/Write on files that haven't been Read | 🛑 Block |
| **Blast radius** | Warns when editing shared code (utils/core/base) | ⚠️ Warn |
| **Irreversible guard** | Blocks `rm -rf`, `git push --force`, `git reset --hard` etc. | 🛑 Block |
| **PixelLab credit guard** | Blocks duplicate descriptions, enforces 15-request batch limit, warns at 50 total | 🛑 Block / ⚠️ Warn |
| **Godot play guard** | Warns when editing Godot scene while game is running | ⚠️ Warn |

**Reasoning tools recognized**: `deep-thinker (think/evaluate/metacog/conclude)`, `sequential-thinking`, `yggdrasil (sequential_thinking/deep_planning)`, `EnterPlanMode`

### 2. PostToolUse Hook (`post_tool_use.py`)

Verifies tool results AFTER execution. Advisory only (always exit 0).

| Check | What it does | Type |
|-------|-------------|------|
| **Write content verification** | After Edit, reads file to confirm `new_string` actually landed | 🔧 Mechanical |
| **GDScript syntax** | Validates bracket/quote balance, missing colons | 🔧 Mechanical |
| **.tscn/.tres structure** | Validates header, node entries, ExtResource references, bracket balance | 🔧 Mechanical |
| **Code modification tracking** | Records modified .gd/.cs files for verification loop | State |
| **Simplicity heuristic** | Flags abstract/interface/factory/singleton patterns, >200 line files | ⚠️ Warn |
| **Repeat error tracker** | Detects 3 consecutive identical errors → warns to change approach | ⚠️ Warn |

### 3. Stop Hook (`stop_hook.py`)

Post-response gatekeeper. Exit 2 = rewake model to fix issues.

| Check | What it does | Type |
|-------|-------------|------|
| **Test verification loop** | State machine: code modified → must verify → check results → idle | 🔧 Mechanical |
| **dotnet build auto-verify** | Detects .cs edits, runs `dotnet build`, blocks on compile errors | 🔧 Mechanical |
| **PixelLab reconciliation** | Detects unverified generations, checks if results were actually reported | 🔧 Mechanical |
| **PixelLab debt check** | Blocks if ≥10 unverified PixelLab generations accumulated | 🔧 Mechanical |
| **Skill invocation check** | Blocks if Skill tool was not called this turn | 🛑 Block |
| **Shallow response detection** | Flags responses with no tool calls, vague language ("should work"), extreme brevity | 🛑 Block |
| **Agent FAIL scan** | Scans guard agent outputs for blocking violations | 🛑 Block |
| **Reasoning state reset** | Clears reasoning flag for next turn | State |
| **Clarify-before-act** | Warns when question and edit appear in same turn | ⚠️ Warn |
| **Memorialize reminder** | Reminds to save design decisions to memory | ⚠️ Warn |

### 4. SessionStart Hook (`session_start.py`)

Injects the mandatory pipeline into system prompt at session start. One-time execution.

## Guard Agents

4 sub-agents run after every response for LLM-level review:

| Agent | Checks |
|-------|--------|
| **Code Review** | Bugs, test coverage, unnecessary dependencies, over-engineering, consistency |
| **Task Tracking** | Completion audit, scope creep, memory save suggestions |
| **Correctness** | Regression prevention, design respect, wrong≠done, upstream>downstream |
| **Behavior** | Disagree-when-wrong, assumption surfacing, anti-rationalization, fail-explicitly |

## Mechanical vs LLM Verification

| | Mechanical (hooks) | LLM (guard agents) |
|---|---|---|
| **Bypassable?** | ❌ No — compiler/file system don't lie | ✅ Yes — can be fooled by convincing text |
| **Checks** | Build errors, file contents, tool call patterns | Logic quality, design consistency, task completeness |
| **Role** | Hard floor — cannot fall below this | Quality ceiling — aspire to this |

## Pipeline (injected by SessionStart)

```
1. Skill check: superpowers-using-superpowers + any applicable skill
2. Godot API? → context7 FIRST. Pixel art? → pixel tools. Editor? → godot-ai.
3. Complex analysis? → sequential-thinking (linear) or yggdrasil (branching)
4. Self-critique: deep-thinker BEFORE responding
5. Respond
```

Steps 1 and 4 are MANDATORY.

## Project Setup

For full hook functionality, add to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python",
        "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"]
      }]
    }],
    "PreToolUse": [{
      "matcher": "Edit|Write|Bash|mcp__godot-ai__.*|mcp__pixellab__.*",
      "hooks": [{
        "type": "command",
        "command": "python",
        "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/pre_tool_use.py"]
      }]
    }],
    "PostToolUse": [{
      "matcher": "Read|Edit|Write|Bash",
      "hooks": [{
        "type": "command",
        "command": "python",
        "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/post_tool_use.py"]
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python",
        "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/stop_hook.py"]
      }]
    }]
  }
}
```

**Important**: The Stop hook's guard agents (defined in plugin.json) are plugin-managed and don't need project-level configuration. SessionStart and all command hooks must be configured at the project level to use `${CLAUDE_PLUGIN_ROOT}`.

## Version History

- **1.3.0**: Mechanical verification system — reasoning-before-edit, write-content check, dotnet build auto-verify, PixelLab reconciliation, .tscn/.tres validation, shallow response detection, Skill enforcement
- **1.2.0**: reasoning-tool-selector skill, session_start hook, 4 guard agents
- **1.1.0**: Initial hooks (pre_tool_use, post_tool_use, stop_hook)
- **1.0.0**: Initial release — cc-rules skill with 98+ behavioral rules
