"""
CUCM Lab Test Bed Teardown — Reverse of provision_testbed.py

Reads testbed-manifest.json and deletes/reverts everything in reverse
dependency order (Phase 7 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1), then reverts
pre-existing objects to their original state.

Connection:
    Host:  10.201.123.107:8443
    Auth:  admin / c1sco123
    AXL:   v15.0, raw SOAP POST (no zeep/WSDL)

Usage:
    PYTHONPATH=. python3.11 tests/migration/cucm/teardown_testbed.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
import urllib3

import requests
from requests.auth import HTTPBasicAuth

# Suppress InsecureRequestWarning for self-signed lab cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Connection details
# ---------------------------------------------------------------------------
HOST = "10.201.123.107"
URL = f"https://{HOST}:8443/axl/"
HEADERS = {"Content-Type": "text/xml", "SOAPAction": "CUCM:DB ver=15.0"}
AUTH = HTTPBasicAuth("admin", "c1sco123")

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
results: list[tuple[str, str, bool]] = []  # (phase, object_desc, success)


def axl_request(soap_body: str) -> tuple[bool, str]:
    """Send a raw AXL SOAP request. Returns (success, response_text)."""
    clean_body = textwrap.dedent(soap_body).strip()
    soap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:ns="http://www.cisco.com/AXL/API/15.0">'
        f'<soapenv:Body>{clean_body}</soapenv:Body>'
        '</soapenv:Envelope>'
    )
    try:
        resp = requests.post(URL, data=soap, headers=HEADERS, auth=AUTH,
                             verify=False, timeout=30)
        is_fault = "Fault" in resp.text
        success = resp.status_code == 200 and not is_fault
        return success, resp.text
    except requests.RequestException as exc:
        return False, str(exc)


def is_not_found(text: str) -> bool:
    """Check if the AXL fault is a 'not found' error (object already gone)."""
    lower = text.lower()
    return ("was not found" in lower
            or "not found" in lower
            or "could not find" in lower
            or "item not valid" in lower)


def log(phase: str, description: str, success: bool, detail: str = "") -> None:
    """Log a result and append to the tracking list."""
    results.append((phase, description, success))
    icon = "OK" if success else "FAIL"
    line = f"  [{icon}] {description}"
    if not success and detail:
        match = re.search(r"<faultstring>(.*?)</faultstring>", detail)
        if match:
            line += f"  -- {match.group(1)}"
        else:
            line += f"  -- {detail[:120]}"
    print(line)


def load_manifest() -> dict:
    """Load testbed-manifest.json from the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, "testbed-manifest.json")
    with open(manifest_path, "r") as f:
        return json.load(f)


# ===================================================================
# Delete created objects (reverse phase order)
# ===================================================================

def delete_phase(phase_label: str, phase_key: str, manifest: dict) -> None:
    """Delete all objects in a phase using manifest metadata."""
    created = manifest.get("created", {})
    phase_data = created.get(phase_key)
    if not phase_data:
        print(f"\n  (no objects found for {phase_key})")
        return

    print(f"\n{'='*60}")
    print(f"Teardown {phase_label}: {phase_data.get('description', '')}")
    print(f"{'='*60}")

    for obj in phase_data.get("objects", []):
        obj_type = obj.get("type", "unknown")
        obj_name = obj.get("name") or obj.get("pattern") or obj.get("userid", "?")

        # --- Users: use SQL delete ---
        if obj.get("delete_sql"):
            sql = obj["delete_sql"]
            # First, clear device associations and CSS to avoid FK constraint issues
            userid = obj.get("userid", "")
            if userid:
                # Clear associated devices before deleting user
                clear_body = f"""<ns:updateEndUser>
                    <userid>{userid}</userid>
                    <associatedDevices></associatedDevices>
                    <callingSearchSpaceName></callingSearchSpaceName>
                </ns:updateEndUser>"""
                ok_clear, text_clear = axl_request(clear_body)
                if ok_clear:
                    log(phase_label, f"Clear associations for {userid}", True)
                elif is_not_found(text_clear):
                    log(phase_label, f"Clear associations for {userid}", True,
                        "(user already gone)")
                else:
                    log(phase_label, f"Clear associations for {userid}", False,
                        text_clear)

            # Execute SQL delete
            body = f"""<ns:executeSQLUpdate>
                <sql>{sql}</sql>
            </ns:executeSQLUpdate>"""
            ok, text = axl_request(body)
            if ok or is_not_found(text):
                log(phase_label,
                    f"SQL DELETE {obj_type} {obj_name}", True,
                    "(already gone)" if is_not_found(text) else "")
            else:
                log(phase_label, f"SQL DELETE {obj_type} {obj_name}", False,
                    text)
            continue

        # --- Standard AXL delete ---
        delete_method = obj.get("delete_method")
        delete_key = obj.get("delete_key")
        if not delete_method or not delete_key:
            log(phase_label,
                f"SKIP {obj_type} {obj_name} (no delete_method/delete_key)",
                False)
            continue

        body = f"<ns:{delete_method}>{delete_key}</ns:{delete_method}>"
        ok, text = axl_request(body)
        if ok:
            log(phase_label, f"Delete {obj_type} {obj_name}", True)
        elif is_not_found(text):
            log(phase_label, f"Delete {obj_type} {obj_name}", True,
                "(already gone)")
        else:
            log(phase_label, f"Delete {obj_type} {obj_name}", False, text)


# ===================================================================
# Revert pre-existing objects
# ===================================================================

def revert_pre_existing(manifest: dict) -> None:
    """Revert modified pre-existing objects to their original state."""
    phase = "Revert"
    pre = manifest.get("pre_existing", {})

    print(f"\n{'='*60}")
    print("Revert pre-existing objects to original state")
    print(f"{'='*60}")

    # --- Revert phones ---
    for phone in pre.get("phones", []):
        if not phone.get("modified"):
            continue
        revert = phone.get("revert")
        if not revert:
            continue

        name = phone["name"]
        method = revert["method"]
        body_xml = revert["body_xml"]
        body = f"<ns:{method}>{body_xml}</ns:{method}>"
        ok, text = axl_request(body)
        if ok:
            log(phase, f"Revert phone {name}", True)
        elif is_not_found(text):
            log(phase, f"Revert phone {name}", True, "(phone not found)")
        else:
            log(phase, f"Revert phone {name}", False, text)

    # --- Revert voicemail profiles ---
    for vm_profile in pre.get("voicemail_profiles", []):
        if not vm_profile.get("modified"):
            continue
        revert = vm_profile.get("revert")
        if not revert:
            continue

        name = vm_profile["name"]
        method = revert["method"]
        body_xml = revert["body_xml"]
        body = f"<ns:{method}>{body_xml}</ns:{method}>"
        ok, text = axl_request(body)
        if ok:
            log(phase, f"Revert VM profile {name}", True)
        elif is_not_found(text):
            log(phase, f"Revert VM profile {name}", True,
                "(profile not found)")
        else:
            log(phase, f"Revert VM profile {name}", False, text)


# ===================================================================
# Summary
# ===================================================================

def print_summary() -> None:
    """Print final summary of all operations."""
    print(f"\n{'='*60}")
    print("TEARDOWN SUMMARY")
    print(f"{'='*60}")

    total = len(results)
    passed = sum(1 for _, _, ok in results if ok)
    failed = total - passed

    # Group by phase
    phases: dict[str, list[tuple[str, bool]]] = {}
    for phase, desc, ok in results:
        phases.setdefault(phase, []).append((desc, ok))

    for phase, items in phases.items():
        phase_ok = sum(1 for _, ok in items if ok)
        phase_fail = len(items) - phase_ok
        status = "ALL PASS" if phase_fail == 0 else f"{phase_fail} FAILED"
        print(f"  {phase}: {phase_ok}/{len(items)} passed ({status})")

    print(f"\n  TOTAL: {passed}/{total} passed, {failed} failed")

    if failed > 0:
        print(f"\n  Failed operations:")
        for phase, desc, ok in results:
            if not ok:
                print(f"    [{phase}] {desc}")


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    """Tear down all testbed objects in reverse dependency order."""
    print("CUCM Lab Test Bed Teardown")
    print(f"Target: {HOST}:8443 (AXL v15.0)")
    print(f"{'='*60}")

    # Load manifest
    print("\nLoading testbed-manifest.json...")
    try:
        manifest = load_manifest()
    except FileNotFoundError:
        print("  ERROR: testbed-manifest.json not found.")
        print("  Expected location: tests/migration/cucm/testbed-manifest.json")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"  ERROR: Invalid JSON in manifest: {exc}")
        sys.exit(1)

    print(f"  CUCM host: {manifest.get('cucm_host', '?')}")
    print(f"  Version:   {manifest.get('cucm_version', '?')}")
    print(f"  Provisioned: {manifest.get('provisioned_date', '?')}")

    # Quick connectivity check
    print("\nConnectivity check...")
    ok, text = axl_request("""<ns:getCCMVersion></ns:getCCMVersion>""")
    if ok:
        match = re.search(r"<version>(.*?)</version>", text)
        ver = match.group(1) if match else "unknown"
        print(f"  Connected to CUCM version {ver}")
    else:
        print("  WARNING: Could not verify CUCM version. Proceeding anyway...")
        print(f"  Response: {text[:200]}")

    # --- Delete created objects in reverse phase order ---
    # Phase 7 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1
    phase_sequence = [
        ("Phase 7", "phase_7_voicemail"),
        ("Phase 6", "phase_6_features"),
        ("Phase 5", "phase_5_routing"),
        ("Phase 4", "phase_4_phones"),
        ("Phase 3", "phase_3_users"),
        ("Phase 2", "phase_2_lines"),
        ("Phase 1", "phase_1_infrastructure"),
    ]

    for phase_label, phase_key in phase_sequence:
        delete_phase(phase_label, phase_key, manifest)

    # --- Revert pre-existing objects ---
    revert_pre_existing(manifest)

    # --- Summary ---
    print_summary()

    # Exit with error code if anything failed
    failed = sum(1 for _, _, ok in results if not ok)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
