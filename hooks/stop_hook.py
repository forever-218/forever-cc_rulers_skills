#!/usr/bin/env python3
"""
Stop hook: gatekeeper — scans agent outputs, rejects stop on blocking violations.
Exit 0 = allow stop. Exit 2 = reject stop, rewake Claude with violation report.
Also handles clarify-before-act detection and memorialize reminders.
"""
import sys, json, os, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

response_text = json.dumps(data, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════════
# 0. Code modified but not tested check
# ═══════════════════════════════════════════════════════════════

MODIFIED_FILE = os.path.expanduser("~/.claude/hook_cache/code_modified.json")
code_was_modified = False
if os.path.exists(MODIFIED_FILE):
    try:
        with open(MODIFIED_FILE) as f:
            mods = json.load(f)
        if mods:
            code_was_modified = True
    except:
        pass

# Check if this turn ran tests or checked logs
test_indicators = [
    "test_run", "test_manage", "logs_read",
    "project_run", "game_eval",
    "Editor Debugger", "Output", "no errors",
    "编译", "通过", "passed", "PASS", "success",
    "验证通过", "测试通过", "运行正常",
]
did_verify = any(ind.lower() in response_text.lower() for ind in test_indicators)

untested_violations = []
if code_was_modified and not did_verify:
    untested_violations.append(
        "CODE UNTESTED: 本轮修改了代码但未运行测试或检查日志。"
        "请用 project_run 跑起来验证功能正常，或用 logs_read 检查是否有编译错误。"
    )

# ═══════════════════════════════════════════════════════════════
# Gatekeeper: scan agent FAIL outputs and decide whether to block
# ═══════════════════════════════════════════════════════════════

# Find all FAIL lines from agents
fail_pattern = re.compile(r'(?:FAIL|fail)\s*[:：]\s*(.+?)(?:\n|$)', re.IGNORECASE)
fails = fail_pattern.findall(response_text)

# Also detect structured JSON violation outputs from agents
violation_pattern = re.compile(r'"violations"\s*:\s*\[(.+?)\]', re.DOTALL | re.IGNORECASE)
for vm in violation_pattern.findall(response_text):
    if vm.strip() and vm.strip() != "[]":
        # Extract individual violations
        items = re.findall(r'"rule"\s*:\s*"([^"]+)"[^}]*"evidence"\s*:\s*"([^"]+)"', vm, re.IGNORECASE)
        for rule, evidence in items:
            fails.append(f"{rule}: {evidence}")

# Blocking rules — these MUST be fixed before stopping
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
    is_blocker = any(br.lower() in f_clean.lower() for br in BLOCK_RULES)
    if is_blocker:
        block_violations.append(f_clean)
    else:
        warn_violations.append(f_clean)

# ═══════════════════════════════════════
# DECISION: block or allow stop
# ═══════════════════════════════════════

block_violations.extend(untested_violations)

if block_violations:
    msg = (
        "\n" + "█" * 62 + "\n"
        "█  ⛔ 守卫 AGENT 检测到严重违规 — 会话被拒绝停止！\n"
        "█  以下问题必须先修复：\n█\n"
    )
    for i, v in enumerate(block_violations, 1):
        msg += f"█    {i}. {v}\n"
    msg += (
        "█\n"
        "█  请立即处理上述违规，修复后重新输出。\n"
        "█  守卫 Agent 会再次审查。全部 PASS 才允许停止。\n"
        + "█" * 62 + "\n"
    )
    # Clear modified flag so next round can re-check
    if os.path.exists(MODIFIED_FILE):
        os.remove(MODIFIED_FILE)
    print(msg, flush=True)
    sys.exit(2)  # Hard block — rewake Claude

# ═══════════════════════════════════════
# Non-blocking warnings
# ═══════════════════════════════════════

if warn_violations:
    print(
        "\n" + "!" * 55 + "\n"
        "  ⚠️  守卫 Agent 发现以下提醒（不阻断停止）：\n"
        + "".join(f"\n    • {v}" for v in warn_violations) +
        "\n" + "!" * 55 + "\n",
        flush=True
    )

# ═══════════════════════════════════════
# Clarify-before-act (non-blocking)
# ═══════════════════════════════════════

has_question = bool(re.search(r'[?？]', response_text))
has_edit_or_write = bool(re.search(r'"tool_name"\s*:\s*"(Edit|Write)"', response_text))

if has_question and has_edit_or_write:
    print(
        "\n" + "!" * 55 + "\n"
        "  ⚠️  Clarify before act: 同时包含提问和编辑操作。\n"
        + "!" * 55 + "\n",
        flush=True
    )

# ═══════════════════════════════════════
# Memorialize reminder (non-blocking)
# ═══════════════════════════════════════

discussion_kw = [
    "决定", "方案", "设计", "架构", "architecture", "design",
    "approach", "decision", "确定", "确认", "agreed", "confirmed"
]
has_discussion = any(kw in response_text.lower() for kw in discussion_kw)
if has_discussion and len(response_text) > 3000:
    print(
        "\n" + "=" * 55 + "\n"
        "  📝 本轮涉及设计决策讨论，若有确认方案请写入记忆。\n"
        + "=" * 55 + "\n",
        flush=True
    )

sys.exit(0)
