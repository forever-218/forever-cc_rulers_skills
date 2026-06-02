#!/usr/bin/env python3
"""
PostToolUse hooks: track reads, verify writes, GDScript validate, repeat error tracker
Receives tool result JSON on stdin. Always exits 0 (advisory only).
"""
import sys, json, os, re

CACHE_DIR = os.path.expanduser("~/.claude/hook_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "read_cache.json")
ERROR_FILE = os.path.join(CACHE_DIR, "error_tracker.json")
MODIFIED_FILE = os.path.join(CACHE_DIR, "code_modified.json")

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

def validate_gdscript(content_text):
    """Basic GDScript syntax validation. Returns list of issues."""
    issues = []
    lines = content_text.split('\n')

    # Check bracket/brace/paren balance
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = []
    for i, line in enumerate(lines, 1):
        for ch in line:
            if ch in pairs:
                stack.append((pairs[ch], i))
            elif ch in pairs.values():
                if not stack or stack[-1][0] != ch:
                    issues.append(f"Line {i}: mismatched closing '{ch}'")
                    break
                else:
                    stack.pop()
    for expected, line_no in stack:
        issues.append(f"Line {line_no}: unclosed '{expected}'")

    # Check string balance (simple heuristic)
    for i, line in enumerate(lines, 1):
        # Count unescaped double quotes
        dq_count = line.count('"') - line.count('\\"')
        if dq_count % 2 != 0:
            issues.append(f"Line {i}: possible unclosed string")

    # Check for common GDScript issues
    joined = '\n'.join(lines)
    # Missing colon after if/elif/else/for/while/func
    for kw in ['if ', 'elif ', 'else', 'for ', 'while ', 'func ']:
        pattern = rf'\b{kw}\b.*[^:]\s*$'
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line) and not line.strip().startswith('#') and ':' not in line:
                issues.append(f"Line {i}: possible missing ':' after '{kw.strip()}'")

    return issues

try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
except Exception:
    sys.exit(0)

# ━━━  Track reads (for read-before-write hook) ━━━
if tool == "Read":
    fp = inp.get("file_path", "")
    if fp:
        cache = read_cache()
        cache.add(fp)
        write_cache(cache)

# ━━━  Write-then-verify + GDScript validation ━━━
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        print(
            f"\n{'~'*50}\n  已修改: {fp}\n  请验证写入内容。修改完记得测试功能。\n{'~'*50}\n",
            flush=True
        )

        # ━ GDScript syntax validation ━
        if fp.endswith(".gd"):
            content = inp.get("content", "") if tool == "Write" else inp.get("new_string", "")
            if content:
                issues = validate_gdscript(content)
                if issues:
                    print(
                        f"\n{'!'*50}\n  ⛔ GDScript 语法警告: {fp}\n"
                        + "\n".join(f"    • {x}" for x in issues[:8]) +
                        f"\n{'!'*50}\n",
                        flush=True
                    )
                else:
                    print(f"  ✓ GDScript 基础语法检查通过: {fp}", flush=True)

        # ━ Track code modification for Agent B ━
        if fp.endswith((".gd", ".cs")):
            mods = {}
            if os.path.exists(MODIFIED_FILE):
                try:
                    with open(MODIFIED_FILE) as f:
                        mods = json.load(f)
                except:
                    pass
            mods[fp] = True
            with open(MODIFIED_FILE, "w") as f:
                json.dump(mods, f)

# ━━━  Simplicity heuristic ━━━
if tool in ("Write", "Edit"):
    fp = inp.get("file_path", "")
    if fp and fp.endswith((".gd", ".cs", ".py", ".tscn", ".tres")):
        content = inp.get("content", "") if tool == "Write" else inp.get("new_string", "")
        if content:
            markers = []
            lower = content.lower()
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
            if fp.endswith(".gd"):
                if lower.count("signal ") > 3:
                    markers.append(f"signals×{lower.count('signal ')}")
                if lower.count("extends ") > 1:
                    markers.append("多层继承")
            lines = content.split("\n")
            if len(lines) > 200:
                markers.append(f"{len(lines)}行")
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

# ━━━  Repeat error tracker ━━━
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
            f"\n{'!'*50}\n  同一错误已出现 {ec['count']} 次！请换一个思路。\n{'!'*50}\n",
            flush=True
        )
else:
    if os.path.exists(ERROR_FILE):
        os.remove(ERROR_FILE)

sys.exit(0)
