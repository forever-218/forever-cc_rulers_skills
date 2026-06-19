#!/usr/bin/env python3
"""
PreToolUse hooks: read-before-write, reasoning-before-edit, blast-radius,
irreversible-guard, hook-tamper-guard, pixellab-guard, godot-play-guard
Receives tool call JSON on stdin. Exit 0=allow, 2=block.
"""
import sys, json, os

CACHE_DIR = os.path.expanduser("~/.claude/hook_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "read_cache.json")
SHARED_DIRS = ["/utils/", "/core/", "/base/", "/common/", "/shared/", "/lib/"]
DESTRUCTIVE = ["rm -rf", "rm -r ", "sudo rm", "git push --force", "git reset --hard",
               "git clean -fd", "git clean -xdf", "deltree", "format "]
# Files exempt from read-before-write AND reasoning-before-edit
EXEMPT_PATTERNS = ["/memory/", "MEMORY.md", "hook_cache", "settings.json"]
# NOTE: /hooks/ intentionally NOT exempt — hooks protect themselves
READONLY_BASH_STARTS = ["ls ", "cd ", "echo ", "pwd", "cat ", "head ", "tail ", "git status",
                        "git log", "git diff", "git stash", "git branch", "git remote",
                        "whoami", "date", "which ", "type ", "find ", "grep ", "rg ",
                        "dotnet --list", "python --version", "node --version", "npm list",
                        "du ", "df ", "wc ", "sort ", "uniq ", "env", "printenv",
                        "gh pr list", "gh issue list"]
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

# 0. Reasoning tracker
if tool in REASONING_TOOLS:
    with open(REASONING_STATE_FILE, "w") as f:
        json.dump({"reasoning_used": True}, f)

if tool == "Skill":
    skill_name = inp.get("skill", "") or inp.get("args", "")
    if any(kw in skill_name.lower() for kw in ["brainstorm", "debug", "plan",
        "superpowers-using", "reasoning-tool"]):
        with open(REASONING_STATE_FILE, "w") as f:
            json.dump({"reasoning_used": True}, f)

# 1. Reasoning-before-edit
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    exempt = any(p in fp for p in EXEMPT_PATTERNS) if fp else False
    if fp and not exempt:
        reasoning_used = False
        if os.path.exists(REASONING_STATE_FILE):
            try:
                with open(REASONING_STATE_FILE) as f:
                    reasoning_used = json.load(f).get("reasoning_used", False)
            except:
                pass
        if not reasoning_used:
            block(
                f"NO REASONING BEFORE EDIT: {fp}\n\n"
                "Rule: reason before editing. Use deep-thinker, sequential-thinking, yggdrasil, or EnterPlanMode first."
            )

if tool == "Bash":
    cmd = inp.get("command", "")
    cmd_stripped = cmd.strip()
    is_readonly = any(cmd_stripped.startswith(s) for s in READONLY_BASH_STARTS)
    is_verify = any(kw in cmd_stripped for kw in ["dotnet build", "dotnet test", "test_run", "logs_read"])
    if not is_readonly and not is_verify:
        reasoning_used = False
        if os.path.exists(REASONING_STATE_FILE):
            try:
                with open(REASONING_STATE_FILE) as f:
                    reasoning_used = json.load(f).get("reasoning_used", False)
            except:
                pass
        if not reasoning_used:
            block(f"NO REASONING BEFORE BASH: {cmd[:80]}")

# 2. Read-before-write
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        exempt = any(p in fp for p in EXEMPT_PATTERNS)
        if not exempt and os.path.exists(fp):
            cache = read_cache()
            if fp not in cache:
                block(f"FILE NOT READ: {fp}\n\nRead before write.")

# 3. Blast radius
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "").replace("\\", "/")
    for sd in SHARED_DIRS:
        if sd in fp:
            warn(f"Shared code: {fp}\nCheck blast radius.")
            break

# 4. Irreversible guard + hook tamper detection
if tool == "Bash":
    cmd = inp.get("command", "")
    cmd_lower = cmd.lower()
    for dp in DESTRUCTIVE:
        if dp.lower() in cmd_lower:
            block(f"DESTRUCTIVE: {cmd}\nConfirm with user first.")
            break

    # Hook tamper: block Bash that targets hook files
    HOOK_FILE_NAMES = ["pre_tool_use.py", "post_tool_use.py", "stop_hook.py", "session_start.py"]
    _is_hook_tamper = False
    if ".claude/hooks/" in cmd or ".claude\\hooks\\" in cmd:
        _is_hook_tamper = True
    else:
        for _hn in HOOK_FILE_NAMES:
            if _hn in cmd:
                _is_hook_tamper = True
                break
    if _is_hook_tamper and not cmd_lower.startswith("python"):
        block(
            f"HOOK TAMPERING: {cmd}\n\n"
            "Cannot delete/move/overwrite hook scripts.\n"
            "Hooks are the defense line. Fix the blocked issue, not delete the guard."
        )

# 5. PixelLab credit guard
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
        st["pending_count"] = 0
        with open(PL_STATE_FILE, "w") as f:
            json.dump(st, f)

    if tool in PIXELLAB_CREATE_TOOLS:
        desc = inp.get("description", "") or inp.get("action_description", "") or ""
        if desc and desc in descriptions:
            block(f"PIXELLAB DUPLICATE: \"{desc}\"\nAlready submitted. Check results first.")
        if pending >= 15:
            block(f"PIXELLAB BATCH LIMIT: {pending} unverified pending. Check results first.")
        if total >= 50:
            warn(f"PIXELLAB USAGE: {total} generations this session. Confirm with user.")

        pending += 1
        total += 1
        st["pending_count"] = pending
        st["total_generations"] = total
        if desc:
            descriptions.add(desc)
            st["descriptions"] = list(descriptions)
        with open(PL_STATE_FILE, "w") as f:
            json.dump(st, f)

# 6. Godot play guard
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
        warn("Godot write operation — ensure editor is not in Play state.")

sys.exit(0)
