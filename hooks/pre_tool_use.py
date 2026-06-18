#!/usr/bin/env python3
"""
PreToolUse hooks: read-before-write, reasoning-before-edit, blast-radius,
irreversible-guard, pixellab-guard, godot-play-guard
Receives tool call JSON on stdin. Exit 0=allow, 2=block.
"""
import sys, json, os

CACHE_DIR = os.path.expanduser("~/.claude/hook_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "read_cache.json")
SHARED_DIRS = ["/utils/", "/core/", "/base/", "/common/", "/shared/", "/lib/"]
DESTRUCTIVE = ["rm -rf", "rm -r ", "sudo rm", "git push --force", "git reset --hard",
               "git clean -fd", "git clean -xdf", "deltree", "format "]
# Files exempt from read-before-write AND reasoning-before-edit checks
EXEMPT_PATTERNS = ["/memory/", "MEMORY.md", "hook_cache", "/hooks/", "settings.json"]
# Bash commands that are read-only — no reasoning required
READONLY_BASH_STARTS = ["ls ", "cd ", "echo ", "pwd", "cat ", "head ", "tail ", "git status",
                        "git log", "git diff", "git stash", "git branch", "git remote",
                        "whoami", "date", "which ", "type ", "find ", "grep ", "rg ",
                        "dotnet --list", "python --version", "node --version", "npm list",
                        "du ", "df ", "wc ", "sort ", "uniq ", "env", "printenv",
                        "gh pr list", "gh issue list"]
# Reasoning tools that count as "depth before action"
REASONING_TOOLS = {
    "mcp__deep-thinker__think", "mcp__deep-thinker__evaluate",
    "mcp__deep-thinker__metacog", "mcp__deep-thinker__conclude",
    "mcp__sequential-thinking__sequentialthinking",
    "mcp__yggdrasil__sequential_thinking", "mcp__yggdrasil__deep_planning",
    "EnterPlanMode",
}
REASONING_STATE_FILE = os.path.join(CACHE_DIR, "reasoning_state.json")

def read_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return set(json.load(f))
    except:
        pass
    return set()

def block(msg):
    print(f"\n{'#'*60}\n#  HOOK BLOCKED\n{'#'*60}\n{msg}\n{'#'*60}\n", flush=True)
    sys.exit(2)

def warn(msg):
    print(f"\n{'~'*60}\n#  HOOK WARNING\n{'~'*60}\n{msg}\n{'~'*60}\n", flush=True)

try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
except Exception:
    sys.exit(0)

os.makedirs(CACHE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 0. Reasoning tracker — mark when reasoning is used
# ═══════════════════════════════════════════════════════════════

if tool in REASONING_TOOLS:
    with open(REASONING_STATE_FILE, "w") as f:
        json.dump({"reasoning_used": True}, f)

# Also count Skill tool with process-oriented skills
if tool == "Skill":
    skill_name = inp.get("skill", "") or inp.get("args", "")
    if any(kw in skill_name.lower() for kw in ["brainstorm", "debug", "plan",
        "superpowers-using", "reasoning-tool"]):
        with open(REASONING_STATE_FILE, "w") as f:
            json.dump({"reasoning_used": True}, f)

# ═══════════════════════════════════════════════════════════════
# 1. Reasoning-before-edit — block fast-path code changes
# ═══════════════════════════════════════════════════════════════

if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    exempt = any(p in fp for p in EXEMPT_PATTERNS) if fp else False
    if fp and not exempt:
        # Check reasoning was used this turn
        reasoning_used = False
        if os.path.exists(REASONING_STATE_FILE):
            try:
                with open(REASONING_STATE_FILE) as f:
                    reasoning_used = json.load(f).get("reasoning_used", False)
            except:
                pass
        if not reasoning_used:
            block(
                f"NO REASONING BEFORE EDIT: 准备修改 {fp}\n\n"
                "规则: 修改代码前必须先深度思考。请先调用以下任一工具:\n"
                "  • deep-thinker (think/evaluate/metacog)\n"
                "  • sequential-thinking\n"
                "  • yggdrasil (sequential_thinking/deep_planning)\n"
                "  • EnterPlanMode (复杂任务)\n\n"
                "禁止「看了就改」——每个修改都必须经过推理验证。"
            )

if tool == "Bash":
    cmd = inp.get("command", "")
    cmd_stripped = cmd.strip()
    # Read-only bash exempt from reasoning check
    is_readonly = any(cmd_stripped.startswith(s) for s in READONLY_BASH_STARTS)
    # Also exempt commands that are clearly verification: dotnet build, test runner
    is_verify = any(kw in cmd_stripped for kw in ["dotnet build", "dotnet test", "test_run", "logs_read"])
    if not is_readonly and not is_verify:
        fp_hint = ""  # Bash has no file_path, check reasoning anyway for significant commands
        reasoning_used = False
        if os.path.exists(REASONING_STATE_FILE):
            try:
                with open(REASONING_STATE_FILE) as f:
                    reasoning_used = json.load(f).get("reasoning_used", False)
            except:
                pass
        if not reasoning_used:
            block(
                f"NO REASONING BEFORE BASH: {cmd[:80]}\n\n"
                "规则: 执行有副作用的命令前必须先深度思考。请先调用 reasoning 工具。\n"
                "豁免: ls/cd/git status/dotnet build 等只读/验证命令。"
            )

# ═══════════════════════════════════════════════════════════════
# 2. Read-before-write
# ═══════════════════════════════════════════════════════════════

if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        exempt = any(p in fp for p in EXEMPT_PATTERNS)
        if not exempt and os.path.exists(fp):
            cache = read_cache()
            if fp not in cache:
                block(
                    f"文件尚未读取: {fp}\n\n"
                    "规则: Read before write — 修改任何文件前必须先读取。\n"
                    "操作: 请先用 Read 工具读取此文件，理解现有逻辑后再修改。"
                )

# ═══════════════════════════════════════════════════════════════
# 3. Blast radius
# ═══════════════════════════════════════════════════════════════

if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "").replace("\\", "/")
    for sd in SHARED_DIRS:
        if sd in fp:
            warn(
                f"修改共享代码: {fp}\n"
                "规则: Blast radius check — 修改 utils/core/base 前请确认。\n"
                "检查: 此文件是否被多个模块引用？改动会影响多少消费者？"
            )
            break

# ═══════════════════════════════════════════════════════════════
# 4. Irreversible guard
# ═══════════════════════════════════════════════════════════════

if tool == "Bash":
    cmd = inp.get("command", "")
    cmd_lower = cmd.lower()
    for dp in DESTRUCTIVE:
        if dp.lower() in cmd_lower:
            block(
                f"检测到破坏性命令: {cmd}\n"
                "规则: 不可逆操作需明确确认。\n"
                "如果这是用户明确要求的操作，请单独确认后再执行。"
            )
            break

# ═══════════════════════════════════════════════════════════════
# 5. PixelLab credit guard
# ═══════════════════════════════════════════════════════════════

PIXELLAB_CREATE_TOOLS = {
    "mcp__pixellab__create_character", "mcp__pixellab__create_1_direction_object",
    "mcp__pixellab__create_8_direction_object", "mcp__pixellab__create_isometric_tile",
    "mcp__pixellab__create_map_object", "mcp__pixellab__create_tiles_pro",
    "mcp__pixellab__create_topdown_tileset", "mcp__pixellab__create_sidescroller_tileset",
    "mcp__pixellab__create_object_state", "mcp__pixellab__create_character_state",
    "mcp__pixellab__animate_character", "mcp__pixellab__animate_object",
}
PIXELLAB_VERIFY_TOOLS = {
    "mcp__pixellab__get_character", "mcp__pixellab__get_object",
    "mcp__pixellab__get_isometric_tile", "mcp__pixellab__get_map_object",
    "mcp__pixellab__get_tiles_pro", "mcp__pixellab__get_topdown_tileset",
    "mcp__pixellab__get_sidescroller_tileset",
    "mcp__pixellab__list_characters", "mcp__pixellab__list_objects",
    "mcp__pixellab__list_isometric_tiles", "mcp__pixellab__list_sidescroller_tilesets",
    "mcp__pixellab__list_topdown_tilesets", "mcp__pixellab__list_tiles_pro",
}

PL_STATE_FILE = os.path.join(CACHE_DIR, "pixellab_state.json")

if tool in PIXELLAB_CREATE_TOOLS or tool in PIXELLAB_VERIFY_TOOLS:
    st = {}
    if os.path.exists(PL_STATE_FILE):
        try:
            with open(PL_STATE_FILE) as f:
                st = json.load(f)
        except:
            st = {}
    pending = st.get("pending_count", 0)
    descriptions = set(st.get("descriptions", []))
    total = st.get("total_generations", 0)

    if tool in PIXELLAB_VERIFY_TOOLS:
        # Verification resets pending counter — model is checking results
        st["pending_count"] = 0
        with open(PL_STATE_FILE, "w") as f:
            json.dump(st, f)

    if tool in PIXELLAB_CREATE_TOOLS:
        desc = inp.get("description", "") or inp.get("action_description", "") or ""

        # Dedup check: same description already submitted
        if desc and desc in descriptions:
            block(
                f"PIXELLAB DUPLICATE: 相同的描述已经提交过:\n  \"{desc}\"\n\n"
                "这个任务已经发送给 PixelLab 了。请先调用 get_* 或 list_* 检查已有结果，"
                "不要重复提交相同的生成请求。重复生成 = 浪费额度。"
            )

        # Batch limit: max 15 pending without verification
        if pending >= 15:
            block(
                f"PIXELLAB BATCH LIMIT: 已有 {pending} 个生成请求未验证结果。\n\n"
                "规则: 每提交一批 PixelLab 生成任务后，必须先调用 get_* 或 list_* 检查已完成的结果，"
                "确认哪些已生成、哪些还需要，然后再继续。\n"
                "禁止不看结果就一股脑提交所有任务。这不仅浪费额度，还会导致重复生成相同内容。"
            )

        # Total warning — soft, just warn
        if total >= 50:
            warn(
                f"⚠️  PIXELLAB 额度警告: 本会话已提交 {total} 次生成请求。\n"
                "请确认: (1) 这是用户明确要求的数量吗？ (2) 大部分结果已验证可用吗？\n"
                "如果额度即将耗尽，请停下来让用户确认是否继续。"
            )

        # Track
        pending += 1
        total += 1
        st["pending_count"] = pending
        st["total_generations"] = total
        if desc:
            descriptions.add(desc)
            st["descriptions"] = list(descriptions)
        with open(PL_STATE_FILE, "w") as f:
            json.dump(st, f)

# ═══════════════════════════════════════════════════════════════
# 6. Godot play guard
# ═══════════════════════════════════════════════════════════════

if "mcp__godot-ai__" in tool:
    write_keywords = [
        "node_create", "node_set_property", "scene_save", "script_create",
        "script_patch", "script_attach", "node_manage", "resource_manage",
        "material_manage", "animation_manage", "particle_manage", "camera_manage",
        "signal_manage", "input_map_manage", "autoload_manage",
        "filesystem_manage", "scene_manage", "theme_manage", "ui_manage",
        "batch_execute"
    ]
    tool_str = json.dumps(inp).lower()
    if any(kw in tool_str for kw in write_keywords):
        warn(
            "Godot 编辑器写操作 — 请确认编辑器不在 Play 状态（F5运行中编辑会导致数据丢失）。\n"
            "如果游戏正在运行，请先停止再编辑。"
        )

sys.exit(0)
