#!/usr/bin/env python3
"""
PreToolUse hooks: read-before-write, blast-radius, irreversible-guard, godot-play-guard
Receives tool call JSON on stdin. Exit 0=allow, 2=block.
"""
import sys, json, os

CACHE_FILE = os.path.expanduser("~/.claude/hook_cache/read_cache.json")
SHARED_DIRS = ["/utils/", "/core/", "/base/", "/common/", "/shared/", "/lib/"]
DESTRUCTIVE = ["rm -rf", "rm -r ", "sudo rm", "git push --force", "git reset --hard",
               "git clean -fd", "git clean -xdf", "deltree", "format "]
# Files exempt from read-before-write check
EXEMPT_PATTERNS = ["/memory/", "MEMORY.md", "hook_cache", "/hooks/", "settings.json"]

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

# ━━━  1. Read-before-write  ━━━
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        # Check exemptions
        exempt = any(p in fp for p in EXEMPT_PATTERNS)
        if not exempt and os.path.exists(fp):
            cache = read_cache()
            if fp not in cache:
                block(
                    f"文件尚未读取: {fp}\n\n"
                    "规则: Read before write — 修改任何文件前必须先读取。\n"
                    "操作: 请先用 Read 工具读取此文件，理解现有逻辑后再修改。"
                )

# ━━━  2. Blast radius  ━━━
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

# ━━━  3. Irreversible guard  ━━━
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

# ━━━  4. Godot play guard  ━━━
if "mcp__godot-ai__" in tool:
    # Write op detection: tools that modify the scene
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
