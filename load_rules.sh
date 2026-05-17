#!/bin/bash
# Load all behavioral rules into the current CC session.
# Usage from any Claude Code window:
#   bash /path/to/load_rules.sh
#
# Reads from the plugin's SKILL.md — works for anyone who clones this repo.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_FILE="$SCRIPT_DIR/skills/cc-rules/SKILL.md"

echo ""
echo "============================================================"
echo "  cc-forever-rules — Behavioral Rules"
echo "============================================================"

if [ -f "$SKILL_FILE" ]; then
    # Strip YAML frontmatter (--- ... ---)
    awk '
    BEGIN { in_front = 0; skip = 0 }
    /^---$/ && !in_front { in_front = 1; skip = 1; next }
    /^---$/ && in_front { skip = 0; next }
    !skip { print }
    ' "$SKILL_FILE"
else
    echo "ERROR: SKILL.md not found at $SKILL_FILE"
    exit 1
fi

echo ""
echo "============================================================"
echo "  All rules loaded."
echo "============================================================"
