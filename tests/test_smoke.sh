#!/usr/bin/env bash
# Smoke test for wxcli — requires WEBEX_ACCESS_TOKEN to be set
set -euo pipefail

echo "=== wxcli smoke test ==="

echo "--- version ---"
wxcli --version

echo "--- whoami ---"
wxcli whoami

echo "--- locations list ---"
wxcli locations list --limit 5

echo "--- users list ---"
wxcli users list --limit 5

echo "--- licenses list ---"
wxcli licenses list --limit 5

echo "--- numbers list ---"
wxcli numbers list --limit 5

echo "--- json output ---"
wxcli locations list --output json --limit 2

echo "=== ALL PASSED ==="
