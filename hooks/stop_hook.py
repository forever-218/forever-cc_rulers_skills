#!/usr/bin/env python3
"""
Stop hook: gatekeeper — test verification loop, agent output scan, behavioral checks.
Exit 0 = allow stop. Exit 2 = reject stop, rewake Claude.
"""
import sys, json, os, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

response_text = json.dumps(data, ensure_ascii=False)
response_lower = response_text.lower()

CACHE_DIR = os.path.expanduser("~/.claude/hook_cache")

# ━━━ TOGGLE: sentinel file disables all agent gatekeeping ━━━
# Create ~/.claude/hook_cache/agents_paused → all agents and gatekeeper skip
# Delete the file → agents resume immediately
# Alternatively, set env: AGENT_GUARD=off
if os.path.exists(os.path.join(CACHE_DIR, "agents_paused")) or os.environ.get("AGENT_GUARD", "").lower() == "off":
    sys.exit(0)
os.makedirs(CACHE_DIR, exist_ok=True)
MODIFIED_FILE = os.path.join(CACHE_DIR, "code_modified.json")
VERIFY_STATE = os.path.join(CACHE_DIR, "verify_state.json")

# ═══════════════════════════════════════════════════════════════
# TEST VERIFICATION LOOP
# State machine: idle → need_verify → need_fix → idle
# ═══════════════════════════════════════════════════════════════

code_was_modified = False
if os.path.exists(MODIFIED_FILE):
    try:
        with open(MODIFIED_FILE) as f:
            mods = json.load(f)
        if mods:
            code_was_modified = True
    except:
        pass

# Verification action detection
ran_tests = any(x in response_lower for x in ["test_run", "test_manage"])
ran_project = any(x in response_lower for x in ["project_run"])
checked_logs = any(x in response_lower for x in ["logs_read"])
ran_game_eval = any(x in response_lower for x in ["game_eval"])

did_verify = ran_tests or (ran_project and checked_logs) or ran_game_eval

# Check verification results for errors
has_test_failures = False
has_log_errors = False

if ran_tests:
    # Check test results for failures
    if any(x in response_lower for x in ["failures:", '"failed":', "FAILED", '"passed": false']):
        has_test_failures = True
    if '"passed":' in response_lower and '"failures":0' not in response_lower and '"failures": 0' not in response_lower:
        # Might have failures
        fail_count_match = re.search(r'"failures"\s*:\s*(\d+)', response_text)
        if fail_count_match and int(fail_count_match.group(1)) > 0:
            has_test_failures = True

if checked_logs:
    if any(x in response_lower for x in ['"level":"error"', "error:", "exception", "traceback", "push_error"]):
        # Exclude known non-errors
        if not any(x in response_lower for x in ["no errors", "0 errors", "error_count: 0"]):
            has_log_errors = True

# ━ State machine ━
verify_state = "idle"
if os.path.exists(VERIFY_STATE):
    try:
        with open(VERIFY_STATE) as f:
            verify_state = json.load(f).get("state", "idle")
    except:
        pass

verify_violations = []

if code_was_modified:
    if not did_verify:
        # Need verification
        verify_violations.append(
            "CODE UNTESTED: 本轮修改了代码但未验证功能。请执行：\n"
            "  1. project_run（跑起来看）+ logs_read(source=\"game\")（查运行日志）\n"
            "  2. 或: test_run（跑单元测试）\n"
            "  3. 或: game_eval（取游戏内状态校验）"
        )
        verify_state = "need_verify"

    elif has_test_failures or has_log_errors:
        # Verification showed errors
        if has_test_failures:
            verify_violations.append(
                "TEST FAILED: 测试未通过，请根据失败输出修复代码后重新验证。"
            )
        if has_log_errors:
            verify_violations.append(
                "LOG ERRORS: 运行日志有错误，请修复后重新跑 project_run + logs_read。"
            )
        verify_state = "need_fix"

    else:
        # Verified and clean!
        verify_state = "idle"
        if os.path.exists(MODIFIED_FILE):
            os.remove(MODIFIED_FILE)
        print("\n" + "=" * 50 + "\n  ✅ 代码验证通过！功能测试无异常。\n" + "=" * 50 + "\n", flush=True)

elif verify_state in ("need_verify", "need_fix"):
    # Previous round needed verification — check if done now
    if did_verify:
        if has_test_failures or has_log_errors:
            if has_test_failures:
                verify_violations.append("TEST FAILED: 修复后测试仍不通过，请继续修复。")
            if has_log_errors:
                verify_violations.append("LOG ERRORS: 修复后仍有错误，请继续修复。")
            verify_state = "need_fix"
        else:
            verify_state = "idle"
            print("\n" + "=" * 50 + "\n  ✅ 验证通过！所有测试/日志无异常。\n" + "=" * 50 + "\n", flush=True)
    else:
        verify_violations.append(
            "VERIFICATION PENDING: 上轮要求验证代码但还未执行。请运行测试或 project_run + logs_read。"
        )

# Save state
with open(VERIFY_STATE, "w") as f:
    json.dump({"state": verify_state}, f)

# ═══════════════════════════════════════════════════════════════
# Gatekeeper: scan agent FAIL outputs
# ═══════════════════════════════════════════════════════════════

fail_pattern = re.compile(r'(?:FAIL|fail)\s*[:：]\s*(.+?)(?:\n|$)', re.IGNORECASE)
fails = fail_pattern.findall(response_text)

violation_pattern = re.compile(r'"violations"\s*:\s*\[(.+?)\]', re.DOTALL | re.IGNORECASE)
for vm in violation_pattern.findall(response_text):
    if vm.strip() and vm.strip() != "[]":
        items = re.findall(r'"rule"\s*:\s*"([^"]+)"[^}]*"evidence"\s*:\s*"([^"]+)"', vm, re.IGNORECASE)
        for rule, evidence in items:
            fails.append(f"{rule}: {evidence}")

BLOCK_RULES = [
    "WRONG=DONE", "wrong equals not done", "wrong=d",
    "COMPLETION", "completion", "task completion",
    "REGRESS", "regress", "don't regress", "dont regress",
    "CORRECTNESS>CONVENIENCE", "correctness over convenience",
    "DIAGNOSTIC VS EDIT", "diagnostic vs edit",
    "SURFACE ASSUMPTIONS", "surface assumptions",
    "UPSTREAM>DOWNSTREAM", "upstream over downstream",
    "SIMPLICITY", "simplest solution",
    "FAIL EXPLICITLY", "fail explicitly",
]

block_violations = []
warn_violations = []

for f in fails:
    f_clean = f.strip().strip('"').strip("'")
    if any(br.lower() in f_clean.lower() for br in BLOCK_RULES):
        block_violations.append(f_clean)
    else:
        warn_violations.append(f_clean)

# ━ Merge verify violations ━
block_violations.extend(verify_violations)

# ═══════════════════════════════════════
# DECISION
# ═══════════════════════════════════════

if block_violations:
    msg = (
        "\n" + "█" * 62 + "\n"
        "█  ⛔ 守卫 Agent 检测到违规 — 会话被拒绝停止！\n"
        "█  以下问题必须先处理：\n█\n"
    )
    for i, v in enumerate(block_violations, 1):
        msg += f"█    {i}. {v}\n"
    msg += (
        "█\n"
        "█  修复完成后重新输出，Agent 会再次审查。\n"
        + "█" * 62 + "\n"
    )
    # Clear modified flag on block
    if os.path.exists(MODIFIED_FILE):
        os.remove(MODIFIED_FILE)
    print(msg, flush=True)
    sys.exit(2)

# ═══════════════════════════════════════
# Non-blocking warnings
# ═══════════════════════════════════════

if warn_violations:
    print(
        "\n" + "!" * 55 + "\n"
        "  ⚠️  守卫提醒（不阻断）：\n"
        + "".join(f"\n    • {v}" for v in warn_violations) +
        "\n" + "!" * 55 + "\n",
        flush=True
    )

# ═══════════════════════════════════════
# Clarify-before-act
# ═══════════════════════════════════════

if re.search(r'[?？]', response_text) and re.search(r'"tool_name"\s*:\s*"(Edit|Write)"', response_text):
    print("\n" + "!" * 55 + "\n  ⚠️  Clarify before act: 同时包含提问和编辑。\n" + "!" * 55 + "\n", flush=True)

# ═══════════════════════════════════════
# Memorialize reminder
# ═══════════════════════════════════════

discussion_kw = ["决定", "方案", "设计", "架构", "architecture", "design", "approach", "decision", "agreed"]
if any(kw in response_lower for kw in discussion_kw) and len(response_text) > 3000:
    print("\n" + "=" * 55 + "\n  📝 有设计决策讨论，记得写入记忆。\n" + "=" * 55 + "\n", flush=True)

sys.exit(0)
