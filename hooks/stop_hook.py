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

# Toggle: sentinel file disables all agent gatekeeping
if os.path.exists(os.path.join(CACHE_DIR, "agents_paused")) or os.environ.get("AGENT_GUARD", "").lower() == "off":
    sys.exit(0)
os.makedirs(CACHE_DIR, exist_ok=True)
MODIFIED_FILE = os.path.join(CACHE_DIR, "code_modified.json")
VERIFY_STATE = os.path.join(CACHE_DIR, "verify_state.json")

# ==============================
# TEST VERIFICATION LOOP
# ==============================

code_was_modified = False
if os.path.exists(MODIFIED_FILE):
    try:
        with open(MODIFIED_FILE) as f:
            mods = json.load(f)
        if mods:
            code_was_modified = True
    except:
        pass

ran_tests = any(x in response_lower for x in ["test_run", "test_manage"])
ran_project = any(x in response_lower for x in ["project_run"])
checked_logs = any(x in response_lower for x in ["logs_read"])
ran_game_eval = any(x in response_lower for x in ["game_eval"])

did_verify = ran_tests or (ran_project and checked_logs) or ran_game_eval

has_test_failures = False
has_log_errors = False

if ran_tests:
    if any(x in response_lower for x in ["failures:", '"failed":', "FAILED", '"passed": false']):
        has_test_failures = True
    if '"passed":' in response_lower and '"failures":0' not in response_lower and '"failures": 0' not in response_lower:
        fail_count_match = re.search(r'"failures"\s*:\s*(\d+)', response_text)
        if fail_count_match and int(fail_count_match.group(1)) > 0:
            has_test_failures = True

if checked_logs:
    if any(x in response_lower for x in ['"level":"error"', "error:", "exception", "traceback", "push_error"]):
        if not any(x in response_lower for x in ["no errors", "0 errors", "error_count: 0"]):
            has_log_errors = True

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
        verify_violations.append(
            "CODE UNTESTED: code modified but not verified. Run project_run + logs_read or test_run."
        )
        verify_state = "need_verify"
    elif has_test_failures or has_log_errors:
        if has_test_failures:
            verify_violations.append("TEST FAILED: fix errors and re-verify.")
        if has_log_errors:
            verify_violations.append("LOG ERRORS: fix errors and re-run project_run + logs_read.")
        verify_state = "need_fix"
    else:
        verify_state = "idle"
        if os.path.exists(MODIFIED_FILE):
            os.remove(MODIFIED_FILE)
        print("\n" + "=" * 50 + "\n  [OK] Code verified clean.\n" + "=" * 50 + "\n", flush=True)
elif verify_state in ("need_verify", "need_fix"):
    if did_verify:
        if has_test_failures or has_log_errors:
            if has_test_failures:
                verify_violations.append("TEST FAILED: still failing. Keep fixing.")
            if has_log_errors:
                verify_violations.append("LOG ERRORS: still have errors. Keep fixing.")
            verify_state = "need_fix"
        else:
            verify_state = "idle"
            print("\n" + "=" * 50 + "\n  [OK] Verification passed.\n" + "=" * 50 + "\n", flush=True)
    else:
        verify_violations.append("VERIFICATION PENDING: verification required but not yet performed.")

with open(VERIFY_STATE, "w") as f:
    json.dump({"state": verify_state}, f)

# ==============================
# Gatekeeper: scan agent FAIL outputs
# ==============================

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

block_violations.extend(verify_violations)

# ==============================
# DECISION (early — before adding SOFT checks)
# ==============================

if block_violations:
    msg = (
        "\n" + "#" * 60 + "\n"
        "  [GUARD BLOCKED] Fix required:\n\n"
    )
    for i, v in enumerate(block_violations, 1):
        msg += f"    {i}. {v}\n"
    msg += (
        "\n  Fix the issues above, then respond again.\n"
        + "#" * 60 + "\n"
    )
    if os.path.exists(MODIFIED_FILE):
        os.remove(MODIFIED_FILE)
    print(msg, flush=True)
    sys.exit(2)

# ==============================
# Non-blocking warnings
# ==============================

if warn_violations:
    print(
        "\n" + "!" * 55 + "\n"
        "  [WARN] Guard notices:\n"
        + "".join(f"\n    * {v}" for v in warn_violations) +
        "\n" + "!" * 55 + "\n",
        flush=True
    )

# ==============================
# Skill invocation check
# ==============================

called_skill = '"tool_name":"Skill"' in response_text or '"tool_name": "Skill"' in response_text
is_local_command_echo = '<local-command-caveat>' in response_text or '<command-name>' in response_text
is_trivial_confirm = len(response_text) < 200 and any(x in response_lower for x in ['ok', 'got it', 'sure'])

if not called_skill and not is_local_command_echo and not is_trivial_confirm:
    block_violations.append(
        "SKILL NOT INVOKED: Skill tool not called this turn."
    )

# ==============================
# Clarify-before-act
# ==============================

if re.search(r'[?？]', response_text) and re.search(r'"tool_name"\s*:\s*"(Edit|Write)"', response_text):
    print("\n" + "!" * 55 + "\n  [WARN] Clarify before act: question + edit in same turn.\n" + "!" * 55 + "\n", flush=True)

# ==============================
# Reasoning state reset
# ==============================

REASONING_STATE_FILE = os.path.join(CACHE_DIR, "reasoning_state.json")
try:
    with open(REASONING_STATE_FILE, "w") as f:
        json.dump({"reasoning_used": False}, f)
except:
    pass

# ==============================
# Shallow response detection
# ==============================

tool_call_count = response_text.count('"tool_name"') or response_text.count('"tool_name":')
has_should_work = any(x in response_lower for x in [
    "should work", "should be fine", "seems fine", "probably works", "might work"
])
has_no_evidence = tool_call_count == 0 and len(response_text) < 2500
is_short_answer = len(response_text) < 800

if not is_local_command_echo and not is_trivial_confirm:
    shallow_signals = []
    if has_no_evidence:
        shallow_signals.append("no tool calls + short response")
    if has_should_work and tool_call_count <= 1:
        shallow_signals.append("vague language ('should work', etc.)")
    if is_short_answer and tool_call_count <= 1:
        shallow_signals.append("very short + no tool calls")

    if shallow_signals:
        block_violations.append(
            "SHALLOW RESPONSE: " + "; ".join(shallow_signals) + ".\n"
            "Rule: correct over fast. Verify, don't guess."
        )

# ==============================
# Method-override detection
# ==============================

declared_override = any(x in response_lower for x in [
    "too slow", "skipping", "i'll just", "i will just",
])
declared_switch = any(x in response_lower for x in [
    "switch to", "switched to", "change to", "batch",
])
has_permission_ask = any(x in response_lower for x in [
    "should i", "shall i", "want me to",
])

if (declared_override or declared_switch) and not has_permission_ask:
    block_violations.append(
        "METHOD OVERRIDE: model changed procedure without asking.\n"
        "Rule: follow user-specified procedure. If faster way exists, propose first — never switch unilaterally."
    )

# ==============================
# PixelLab result reconciliation — MECHANICAL
# ==============================

PL_STATE_FILE = os.path.join(CACHE_DIR, "pixellab_state.json")
PL_CREATE_SIGNAL = "mcp__pixellab__create_" in response_text or "mcp__pixellab__animate_" in response_text
PL_VERIFY_SIGNAL = any(x in response_text for x in [
    "mcp__pixellab__get_", "mcp__pixellab__list_"
])

if PL_CREATE_SIGNAL and not PL_VERIFY_SIGNAL:
    block_violations.append(
        "PIXELLAB UNVERIFIED: create/animate called without get_*/list_* check."
    )
elif PL_CREATE_SIGNAL and PL_VERIFY_SIGNAL:
    has_specific_count = bool(re.search(r'(?:count|total)\s*[:：]?\s*\d+', response_lower))
    has_status_report = any(x in response_lower for x in [
        "completed", "success", "failed", "progress", "pending"
    ])
    if not has_specific_count and not has_status_report:
        block_violations.append(
            "PIXELLAB DODGED: get_*/list_* called but no specific results reported.\n"
            "Must output: actual count, success/fail, remaining."
        )

_pl_pending = 0
if os.path.exists(PL_STATE_FILE):
    try:
        with open(PL_STATE_FILE) as f:
            _pl_st = json.load(f)
        _pl_pending = _pl_st.get("pending_count", 0)
    except:
        pass
if _pl_pending >= 10 and not PL_VERIFY_SIGNAL:
    block_violations.append(
        f"PIXELLAB DEBT: {_pl_pending} unverified generation requests accumulated.\n"
        "Must list_* before continuing."
    )

# ==============================
# dotnet build auto-verification — MECHANICAL
# ==============================

_cs_modified = False
_cs_files = []
if os.path.exists(MODIFIED_FILE):
    try:
        with open(MODIFIED_FILE) as f:
            mods = json.load(f)
        _cs_files = [fp for fp in mods if fp.endswith(".cs")]
        if _cs_files:
            _cs_modified = True
    except:
        pass

if _cs_modified and _cs_files:
    _project_root = None
    _csproj = None
    _test_dir = os.path.dirname(os.path.abspath(_cs_files[0]))
    for _ in range(6):
        try:
            for _f in os.listdir(_test_dir):
                if _f.endswith(".csproj") and not _f.endswith("Tests.csproj"):
                    _csproj = os.path.join(_test_dir, _f)
                    _project_root = _test_dir
                    break
        except:
            pass
        if _csproj:
            break
        _parent = os.path.dirname(_test_dir)
        if _parent == _test_dir:
            break
        _test_dir = _parent

    if _csproj and _project_root:
        try:
            import subprocess
            _result = subprocess.run(
                ["dotnet", "build", _csproj, "--nologo", "-v", "q"],
                cwd=_project_root,
                capture_output=True, text=True, timeout=45
            )
            _build_output = (_result.stdout + _result.stderr).strip()
            if _result.returncode != 0:
                _error_lines = []
                for _line in _build_output.split('\n'):
                    if 'error CS' in _line or 'error :' in _line:
                        _error_lines.append(_line.strip()[-200:])
                if not _error_lines:
                    _error_lines = _build_output.split('\n')[-15:]
                block_violations.append(
                    "DOTNET BUILD FAILED:\n"
                    + "\n".join(f"  {el}" for el in _error_lines[:12])
                )
            else:
                print("\n" + "=" * 50 + "\n  [MECHANICAL] dotnet build: PASSED\n" + "=" * 50 + "\n", flush=True)
                if os.path.exists(MODIFIED_FILE):
                    os.remove(MODIFIED_FILE)
        except subprocess.TimeoutExpired:
            print("\n  [MECHANICAL] dotnet build: TIMEOUT (>45s)\n", flush=True)
        except FileNotFoundError:
            print("\n  [MECHANICAL] dotnet build: dotnet CLI not found\n", flush=True)
        except Exception as _e:
            print(f"\n  [MECHANICAL] dotnet build: error ({_e})\n", flush=True)

# ==============================
# Memorialize reminder
# ==============================

discussion_kw = ["decision", "architecture", "design", "approach"]
if any(kw in response_lower for kw in discussion_kw) and len(response_text) > 3000:
    print("\n" + "=" * 55 + "\n  [REMINDER] Design discussion — save to memory.\n" + "=" * 55 + "\n", flush=True)

sys.exit(0)
