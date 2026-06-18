#!/usr/bin/env python3
"""SessionStart hook — injects mandatory pipeline rules BEFORE model starts thinking."""
import sys

print("""<SYSTEM_INJECTION_PRIORITY_HIGHEST>
MANDATORY PIPELINE — every response must follow this order:

1. Skill check: superpowers-using-superpowers + any applicable skill
2. Godot API? → context7 FIRST. Pixel art? → pixel tools. Editor? → godot-ai.
3. Complex analysis? → sequential-thinking (linear) or yggdrasil (branching)
4. Self-critique: deep-thinker BEFORE responding — find blind spots, fix them
5. Respond

Steps 1 and 4 are MANDATORY. Skipping them violates explicit user requirements.
</SYSTEM_INJECTION_PRIORITY_HIGHEST>""")

sys.exit(0)
