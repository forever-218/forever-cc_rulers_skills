#!/usr/bin/env python3
"""
PostToolUse hooks: track reads, verify writes, repeat error tracker
Receives tool result JSON on stdin. Always exits 0 (advisory only).
"""
import sys, json, os

CACHE_DIR = os.path.expanduser("~/.claude/hook_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "read_cache.json")
ERROR_FILE = os.path.join(CACHE_DIR, "error_tracker.json")

def read_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return set(json.load(f))
    except:
        pass
    return set()

def write_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(sorted(list(data)), f)

try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
except Exception:
    sys.exit(0)

# ━━━  5. Track reads (for read-before-write hook)  ━━━
if tool == "Read":
    fp = inp.get("file_path", "")
    if fp:
        cache = read_cache()
        cache.add(fp)
        write_cache(cache)

# ━━━  6. Write-then-verify  ━━━
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        print(
            f"\n{'~'*50}\n  已修改: {fp}\n  请验证写入内容是否正确。修改完记得测试功能。\n{'~'*50}\n",
            flush=True
        )

# ━━━  6c. Simplicity heuristic  ━━━
if tool in ("Write", "Edit"):
    fp = inp.get("file_path", "")
    if fp and fp.endswith((".gd", ".cs", ".py", ".tscn", ".tres")):
        content = inp.get("content", "") if tool == "Write" else inp.get("new_string", "")
        if content:
            markers = []
            lower = content.lower()
            # Abstract / interface patterns
            if "abstract" in lower or "abc" in lower:
                markers.append("abstract/ABC")
            if "interface" in lower and fp.endswith(".cs"):
                markers.append("interface")
            if "factory" in lower:
                markers.append("factory")
            if "singleton" in lower:
                markers.append("singleton")
            if "dependency" in lower and "injection" in lower:
                markers.append("DI")
            # GDScript: excessive signals
            if fp.endswith(".gd"):
                sig_count = lower.count("signal ")
                if sig_count > 3:
                    markers.append(f"signals×{sig_count}")
                ext_count = lower.count("extends ")
                if ext_count > 1:
                    markers.append("多层继承")
            # Line count check
            lines = content.split("\n")
            if len(lines) > 200:
                markers.append(f"{len(lines)}行")
            # Class count in one file
            cls_count = lower.count("class ") + lower.count("class_name ")
            if cls_count > 3:
                markers.append(f"classes×{cls_count}")

            if markers:
                print(
                    f"\n{'~'*50}\n  ⚠️  复杂度提醒: {fp}\n"
                    f"  检测到: {', '.join(markers)}\n"
                    f"  规则: Simplest solution first — 确保这是最简单方案。\n{'~'*50}\n",
                    flush=True
                )

# ━━━  6b. Repeat error tracker  ━━━
# Check if the tool result indicates an error
result_str = json.dumps(data).lower()
is_error = any(word in result_str for word in ["error", "failed", "exception", "traceback"])

try:
    ec = {}
    if os.path.exists(ERROR_FILE):
        with open(ERROR_FILE) as f:
            ec = json.load(f)
except:
    ec = {}

if is_error:
    # Create a fingerprint of the error: tool name + first 200 chars of input
    fingerprint = f"{tool}:{json.dumps(inp)[:200]}"
    if fingerprint == ec.get("last_fingerprint", ""):
        ec["count"] = ec.get("count", 0) + 1
    else:
        ec["count"] = 1
        ec["last_fingerprint"] = fingerprint

    with open(ERROR_FILE, "w") as f:
        json.dump(ec, f)

    if ec["count"] >= 3:
        print(
            f"\n{'!'*50}\n  同一错误已出现 {ec['count']} 次！请换一个思路，不要继续重试。\n{'!'*50}\n",
            flush=True
        )
else:
    # Reset error tracker on success
    if os.path.exists(ERROR_FILE):
        os.remove(ERROR_FILE)

sys.exit(0)
