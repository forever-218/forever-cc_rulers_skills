# Tool Coordination Rules

This skill coordinates ALL your tools — MCP servers, built-in tools, and skills.
It describes tool CATEGORIES and purposes. Map them to whatever tools are actually available.

## The Pipeline (every response)

```
1. Skill check: any skill apply? → invoke Skill tool
2. Need API docs for a framework/library? → documentation tool FIRST
3. Complex analysis? → reasoning tool (single-path or multi-path)
4. BEFORE responding → self-critique tool
5. Respond, incorporating critique findings
```

Steps 1 and 4 are MANDATORY. Steps 2 and 3 are conditional.

---

## Tool Categories — Match to Available Tools

### Category A: Reasoning Tools

Scan your tool list for tools with names or descriptions matching:
"thinking", "reasoning", "sequential", "tree of thoughts", "deep think", "critique", "self-reflection"

| Sub-type | Use when | Expected cost |
|---|---|---|
| **Single-path reasoning** | Trace a bug, analyze one function, check one edge case. One cause → one answer. | Low |
| **Multi-path reasoning** | System design, architecture choice, "should I do A or B". Multiple valid approaches. | Medium-High |
| **Self-critique** | EVERY response. Examine your own reasoning: blind spots, assumptions, rationalization. Fix issues BEFORE responding. | Low |

Pick ONE single-path OR multi-path tool per complex task. Self-critique is separate — always use it.

### Category B: Documentation Tools

Scan for tools matching: "docs", "documentation", "context", "api reference", "library lookup"

Use BEFORE writing framework/library-specific code. Never guess API names.

### Category C: Editor/IDE Tools

Scan for tools matching: "editor", "IDE", "scene", "project", "node", "debugger"

Use for: creating/modifying project files, running builds, reading errors, managing assets.

### Category D: File Tools

Scan for tools matching: "filesystem", "file", "read", "write"

Use when native Read/Write tools are blocked, or for batch operations.

### Category E: Asset/Creative Tools

Scan for tools matching: "sprite", "image", "pixel", "texture", "model", "audio", "generate"

Use for: creating or editing visual/audio assets.

---

## Decision Flow

```
User message received
│
├─ Need docs for a framework? → documentation tool FIRST
├─ Need to create/edit assets? → asset tools
├─ Need to manipulate project? → editor tools
├─ Need to read/write files? → file tools
│
├─ Simple response? → self-critique tool → respond
├─ Complex problem? → single-path or multi-path reasoning → self-critique → respond
├─ Creative/design work? → brainstorming skill FIRST → then above
├─ Bug/unexpected behavior? → debugging skill FIRST → reasoning → self-critique
```

---

## Rules

1. Skill tool check BEFORE every response — "just a simple question" is never an excuse
2. Self-critique tool BEFORE every final response — find and fix your own mistakes
3. Documentation tool BEFORE writing framework-specific code — never guess APIs
4. Single-path OR multi-path reasoning — never both in one response
5. If unsure which reasoning type → default to single-path (cheapest)
6. Map these categories to WHATEVER tools are available in your session — tool names vary
