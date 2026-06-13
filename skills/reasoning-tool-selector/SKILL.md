# Full MCP & Skill Pipeline

You have 6 MCP servers and 30+ skills. This file coordinates ALL of them.

## The Pipeline (every response)

```
1. Superpowers check: any skill apply? → invoke Skill tool
2. Need up-to-date Godot/C# API docs? → context7
3. Complex analysis? → sequential-thinking OR yggdrasil
4. BEFORE responding → deep-thinker (self-critique)
5. Respond, incorporating critique findings
```

Steps 1 and 4 are mandatory. Steps 2 and 3 are conditional.

---

## ALL MCP Servers — When to Use

### Reasoning (pick ONE)

| MCP | Use when | Token cost |
|---|---|---|
| `mcp__sequential-thinking__sequential_thinking` | Single-path: trace a bug, analyze one function, check one edge case | 1x |
| `mcp__yggdrasil__sequential_thinking` | Multi-path: system design, architecture choice, "should I do A or B" | 1.5-2x |
| `mcp__deep-thinker__deepthink` | EVERY response. Self-critique: blind spots, assumptions, rationalizations | 1x |

### Godot Development

| MCP | Use when |
|---|---|
| `mcp__godot-ai__*` (150+ tools) | Creating nodes, setting properties, running project, editing scenes, debugging in-editor |
| `mcp__context7__query-docs` + `resolve-library-id` | Looking up Godot 4.x API, C# bindings, GDScript methods. Use BEFORE writing engine code. |

### Files

| MCP | Use when |
|---|---|
| `mcp__filesystem__*` | Reading/writing files in project dirs. Use when Edit/Write/Bash are blocked or for batch operations. |

### Pixel Art

| MCP | Use when |
|---|---|
| `mcp__pixel__*` | Creating sprites, animations, tilesets, palettes, dithering, exporting spritesheets |

---

## Decision Flow

```
User message received
│
├─ About Godot API? → context7 FIRST, then respond
├─ About pixel art? → pixel tools
├─ Need to edit Godot scene? → godot-ai tools
├─ Need to read/write files? → filesystem tools
│
├─ Simple question? → deep-thinker → respond
├─ Complex problem? → sequential-thinking/yggdrasil → deep-thinker → respond
├─ Creative work? → superpowers-brainstorming FIRST → then above
├─ Bug? → superpowers-systematic-debugging FIRST → sequential-thinking → deep-thinker
```

---

## Rules

1. Superpowers skills ALWAYS before reasoning tools
2. context7 ALWAYS before writing Godot API code
3. deep-thinker ALWAYS before final response
4. sequential-thinking OR yggdrasil — never both
5. If unsure which reasoning tool → default to sequential-thinking (cheapest)
6. Token cost is accepted. Do NOT skip steps to save tokens.
