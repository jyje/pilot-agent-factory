"""Diagnostic script: ENV settings, endpoint availability, inference, discovery.

Usage: uv run python doctor.py
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PASS = "  [PASS]"
FAIL = "  [FAIL]"
SKIP = "  [SKIP]"
SEP = "-" * 52


def section(title: str) -> None:
    print(f"\n{SEP}\n {title}\n{SEP}")


def check(label: str, ok: bool, detail: str = "") -> bool:
    line = f"{PASS if ok else FAIL} {label}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    return ok


# ── 1. ENV ──────────────────────────────────────────────

section("1. Environment Variables")

api_key = os.getenv("ANTHROPIC_API_KEY", "")
base_url = os.getenv("ANTHROPIC_BASE_URL", "")
main_model = os.getenv("MAIN_MODEL", "claude-sonnet-4-6")

env_ok = check("ANTHROPIC_API_KEY is set", bool(api_key),
               f"value: {api_key[:16]}..." if api_key else "not set")
check("ANTHROPIC_BASE_URL", True,
      f"value: {base_url}" if base_url else "not set — using official Anthropic API")
env_ok &= check("MAIN_MODEL", True, f"value: {main_model}")


# ── 2. API Connectivity ─────────────────────────────────

section("2. API Connectivity")

if not api_key:
    print(f"{SKIP} connectivity — ANTHROPIC_API_KEY not configured")
    conn_ok = False
else:
    models_url = (f"{base_url.rstrip('/')}/v1/models" if base_url
                  else "https://api.anthropic.com/v1/models")
    req = urllib.request.Request(
        models_url, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            status, body = resp.status, resp.read(256).decode()
    except urllib.error.HTTPError as e:
        status, body = e.code, str(e.reason)
    except Exception as e:
        status, body = 0, str(e)
    conn_ok = check(f"GET {models_url}", status == 200,
                    f"HTTP {status}" + (f": {body[:80]}" if status != 200 else ""))


# ── 3. Agent Discovery (no LLM required) ────────────────

section("3. Agent Discovery")

try:
    from agent_factory_sdk import AgentRegistry

    registry = AgentRegistry().discover(dropin_dir=Path(__file__).parent / "dropins")
    names = sorted(registry.agents)
    disco_ok = check(f"entry points + dropins loaded ({len(names)} agents)",
                     len(names) >= 4, f"agents: {', '.join(names)}")
    disco_ok &= check("no load failures", not registry.errors,
                      "; ".join(f"{e.source}: {e.error}" for e in registry.errors))
except Exception as e:
    print(f"{FAIL} discovery error: {e}")
    disco_ok = False


# ── 4. Basic Inference ──────────────────────────────────

section("4. Basic Inference")

if not env_ok or not conn_ok:
    print(f"{SKIP} inference — fix ENV / connectivity first")
    infer_ok = False
else:
    try:
        from agent_factory_sdk import make_model
        from langchain_core.messages import HumanMessage

        resp = make_model().invoke([HumanMessage(content="Reply with exactly: OK")])
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        infer_ok = check(f"MAIN_MODEL inference ({main_model})", bool(text),
                         f"response: {text[:60]!r}")
    except Exception as e:
        print(f"{FAIL} inference error: {e}")
        infer_ok = False


# ── Summary ─────────────────────────────────────────────

section("Summary")
all_ok = True
for name, ok in {
    "ENV": env_ok, "Connectivity": conn_ok, "Discovery": disco_ok, "Inference": infer_ok,
}.items():
    check(name, ok)
    all_ok &= ok

print()
print("All checks passed. Ready to run main.py." if all_ok
      else "Some checks failed. See details above (is LM Studio's local server running?).")
sys.exit(0 if all_ok else 1)
