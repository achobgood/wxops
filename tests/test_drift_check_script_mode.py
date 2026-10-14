"""`python tools/drift_check.py` (bare-script form) must not crash.

Run as a script, Python puts `tools/` (not the repo root) on sys.path, so every
`from tools import …` raises ImportError. drift_check's own fallbacks then
imported `generate_commands` bare — but that module itself does
`from tools.openapi_parser import …`, so check_inert_overrides crashed the whole
gate (exit 2, "result: CRASHED"). CI and the weekly spec-sync routine use the
`python -m tools.drift_check` form and were never affected; this pins the
documented script form too.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"


def test_bare_script_form_imports_the_tools_package(tmp_path):
    # Mimic `python tools/drift_check.py`: tools/ first on sys.path, the repo root
    # absent, run from an unrelated cwd. check_inert_overrides is the code path
    # that crashed (it imports generate_commands -> tools.openapi_parser).
    code = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(TOOLS)!r}); "
        f"g = runpy.run_path({str(TOOLS / 'drift_check.py')!r}, run_name='drift_check_script'); "
        "g['check_inert_overrides']()"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
