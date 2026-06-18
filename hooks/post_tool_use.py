#!/usr/bin/env python3
"""
PostToolUse hooks: track reads, content-change verification, GDScript validate, repeat error tracker
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
        dq_count = line.count('"') - line.count('\\"')
        if dq_count % 2 != 0:
            issues.append(f"Line {i}: possible unclosed string")

    joined = '\n'.join(lines)
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

# Track reads (for read-before-write hook)
if tool == "Read":
    fp = inp.get("file_path", "")
    if fp:
        cache = read_cache()
        cache.add(fp)
        write_cache(cache)

# Write-then-verify + mechanical content verification + GDScript validation
if tool in ("Edit", "Write"):
    fp = inp.get("file_path", "")
    if fp:
        # MECHANICAL: for Edit, verify new_string actually landed in the file
        if tool == "Edit" and fp.endswith((".cs", ".gd", ".py", ".json", ".tscn", ".tres")):
            new_str = inp.get("new_string", "")
            if new_str and os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        actual = f.read()
                    if new_str not in actual:
                        print(
                            f"\n{'!'*55}\n"
                            f"  [MECHANICAL FAIL] WRITE NOT APPLIED: {fp}\n"
                            f"  old_string did not match or new_string not found in file.\n"
                            f"  LLM claimed edit but file unchanged. Read + re-Edit required.\n"
                            f"{'!'*55}\n",
                            flush=True
                        )
                    else:
                        print(f"  [MECHANICAL] Write verified: new_string in file", flush=True)
                except Exception as e:
                    print(f"  [MECHANICAL] Write verify skipped ({e})", flush=True)

        print(
            f"\n{'~'*50}\n  MODIFIED: {fp}\n  Verify the change. Test after editing.\n{'~'*50}\n",
            flush=True
        )

        # GDScript syntax validation
        if fp.endswith(".gd"):
            content = inp.get("content", "") if tool == "Write" else inp.get("new_string", "")
            if content:
                issues = validate_gdscript(content)
                if issues:
                    print(
                        f"\n{'!'*50}\n  GDScript syntax warnings: {fp}\n"
                        + "\n".join(f"    - {x}" for x in issues[:8]) +
                        f"\n{'!'*50}\n",
                        flush=True
                    )
                else:
                    print(f"  GDScript basic syntax OK: {fp}", flush=True)

        # Track code modification for verification loop
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

# Simplicity heuristic
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
                    markers.append(f"signals x{lower.count('signal ')}")
                if lower.count("extends ") > 1:
                    markers.append("multi-extends")
            lines = content.split("\n")
            if len(lines) > 200:
                markers.append(f"{len(lines)} lines")
            cls_count = lower.count("class ") + lower.count("class_name ")
            if cls_count > 3:
                markers.append(f"{cls_count} classes")
            if markers:
                print(
                    f"\n{'~'*50}\n"
                    f"  COMPLEXITY: {fp}\n"
                    f"  Detected: {', '.join(markers)}\n"
                    f"  Rule: Simplest solution first.\n"
                    f"{'~'*50}\n",
                    flush=True
                )

# Repeat error tracker
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
            f"\n{'!'*50}\n  Same error {ec['count']} times! Change approach.\n{'!'*50}\n",
            flush=True
        )
else:
    if os.path.exists(ERROR_FILE):
        os.remove(ERROR_FILE)

sys.exit(0)
