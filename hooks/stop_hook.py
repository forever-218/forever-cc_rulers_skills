#!/usr/bin/env python3
"""
Stop hooks: memorialize decisions, clarify-before-act detection
Receives session/response JSON on stdin. Always exits 0 (advisory only).
"""
import sys, json, os, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

response_text = json.dumps(data, ensure_ascii=False)

# ━━━  7. Clarify-before-act: detect question + edit in same response  ━━━
has_question = bool(re.search(r'[?？]', response_text))
# Check if tool calls include Edit or Write
has_edit_or_write = False
if "tool_calls" in response_text or "tool_name" in response_text:
    # Look for Edit or Write tool names in the response
    if re.search(r'"tool_name"\s*:\s*"(Edit|Write)"', response_text):
        has_edit_or_write = True

if has_question and has_edit_or_write:
    print(
        "\n" + "!"*55 + "\n"
        "  ⚠️  检测到本响应同时包含提问和编辑/写入操作！\n"
        "  规则: Clarify before act — 问完问题应先等用户回答再动手。\n"
        "  请检查: 是否应该等用户回复后再执行修改？\n"
        + "!"*55 + "\n",
        flush=True
    )

# ━━━  7b. Memorialize decisions reminder  ━━━
discussion_keywords = [
    "决定", "方案", "设计", "架构", "architecture", "design",
    "approach", "decision", "确定", "确认", "agreed", "confirmed"
]
has_discussion = any(kw in response_text.lower() for kw in discussion_keywords)
conv_size = len(response_text)

if has_discussion and conv_size > 3000:
    print(
        "\n" + "="*55 + "\n"
        "  📝 本次对话涉及设计决策讨论。\n"
        "  如有确认的方案，请写入项目记忆系统:\n"
        "  - Write MEMORY.md 索引行\n"
        "  - Write .md 记忆文件 (决策 + 理由 + 已否定的备选)\n"
        "  这能防止未来对话重复踩坑。\n"
        + "="*55 + "\n",
        flush=True
    )

sys.exit(0)
