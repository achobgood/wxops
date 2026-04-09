#!/usr/bin/env python3.11
"""Build the Layer 3 benchmark fixture store.

Creates tests/fixtures/benchmark-migration/migration.db with 20 decisions
covering all four fixture categories: recommended, dissent-trigger, gotcha-path,
and normal. Run this script whenever the MigrationStore schema changes.

Usage: python3.11 tools/build_benchmark_fixture.py
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from wxcli.migration.store import MigrationStore

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "benchmark-migration"
DB_PATH = FIXTURE_DIR / "migration.db"

DECISIONS = [
    # --- Recommended decisions (4) ---
    {
        "decision_id": "D0001",
        "type": "DEVICE_INCOMPATIBLE",
        "severity": "HIGH",
        "summary": "CP-7911 has no direct Webex MPP equivalent",
        "context": {"model": "CP-7911", "count": 3},
        "options": [
            {"id": "skip", "label": "Skip device", "impact": "Device not migrated"},
            {"id": "replace", "label": "Replace with 9841", "impact": "Hardware purchase required"},
        ],
        "recommendation": "skip",
        "recommendation_reasoning": "CP-7911 is incompatible with Webex. No firmware conversion path exists. Skip and plan hardware replacement.",
    },
    {
        "decision_id": "D0002",
        "type": "FEATURE_APPROXIMATION",
        "severity": "MEDIUM",
        "summary": "Hunt group HG-Support has 3 agents and no queue features",
        "context": {"agent_count": 3, "queue_enabled": False, "pilot": "3000"},
        "options": [
            {"id": "hunt_group", "label": "Hunt Group", "impact": "Direct equivalent"},
            {"id": "call_queue", "label": "Call Queue", "impact": "Adds queue behavior"},
        ],
        "recommendation": "hunt_group",
        "recommendation_reasoning": "3 agents, no queue indicators. Hunt Group is the direct equivalent.",
    },
    {
        "decision_id": "D0003",
        "type": "CSS_ROUTING_MISMATCH",
        "severity": "MEDIUM",
        "summary": "CSS-Standard scope differs from Webex location calling",
        "context": {"scope_difference": True, "ordering_dependency": False, "css_name": "CSS-Standard"},
        "options": [
            {"id": "use_union", "label": "Use union scope", "impact": "All partitions accessible"},
            {"id": "manual", "label": "Manual partition mapping", "impact": "Operator must map each partition"},
        ],
        "recommendation": "use_union",
        "recommendation_reasoning": "Scope difference only, no partition ordering dependency. Union scope preserves routing reach.",
    },
    {
        "decision_id": "D0004",
        "type": "MISSING_DATA",
        "severity": "LOW",
        "summary": "Trunk SIP-PSTN is missing password",
        "context": {"field": "trunk_password", "trunk_name": "SIP-PSTN"},
        "options": [
            {"id": "generate", "label": "Generate password", "impact": "Auto-generated secure password"},
            {"id": "skip", "label": "Skip trunk", "impact": "Trunk not migrated"},
        ],
        "recommendation": "generate",
        "recommendation_reasoning": "Trunk passwords can be auto-generated. No CUCM value to preserve.",
    },
    # --- Dissent trigger decisions (2) ---
    {
        "decision_id": "D0005",
        "type": "CSS_ROUTING_MISMATCH",
        "severity": "HIGH",
        "summary": "CSS-Ordering relies on partition ordering for overlapping patterns",
        "context": {"scope_difference": True, "ordering_dependency": True, "css_name": "CSS-Ordering",
                    "partitions": ["PT-Internal", "PT-External", "PT-LD"]},
        "options": [
            {"id": "use_union", "label": "Use union scope", "impact": "May route differently — ordering lost"},
            {"id": "manual", "label": "Manual mapping", "impact": "Operator defines routing per pattern"},
        ],
        "recommendation": "manual",
        "recommendation_reasoning": "Partition ordering dependency detected. Webex uses longest-match; ordering semantics cannot be preserved with union scope.",
    },
    {
        "decision_id": "D0006",
        "type": "FEATURE_APPROXIMATION",
        "severity": "MEDIUM",
        "summary": "Hunt group HG-Sales has 6 agents, queue behavior ambiguous",
        "context": {"agent_count": 6, "queue_enabled": True, "pilot": "2000"},
        "options": [
            {"id": "hunt_group", "label": "Hunt Group", "impact": "No queue visibility"},
            {"id": "call_queue", "label": "Call Queue", "impact": "Queue stats + hold music"},
        ],
        "recommendation": None,
        "recommendation_reasoning": None,
    },
    # --- Gotcha-path triggers (3) ---
    {
        "decision_id": "D0007",
        "type": "MISSING_DATA",
        "severity": "HIGH",
        "summary": "Location Dallas is missing street address",
        "context": {"field": "location_address", "location_name": "Dallas"},
        "options": [
            {"id": "skip", "label": "Skip location", "impact": "All Dallas objects skipped"},
            {"id": "manual", "label": "Enter address manually", "impact": "Operator provides address"},
        ],
        "recommendation": "manual",
        "recommendation_reasoning": "Webex requires a street address for every location. Dallas must have one before objects can be created.",
    },
    # D0008 and D0009 are not store decisions — they are gotcha triggers
    # activated via mock tool responses (wxcli whoami, wxcli cucm preflight).
    # See tool_responses/ for the mock outputs.
    # --- Normal decisions (11) ---
    {
        "decision_id": "D0010",
        "type": "VOICEMAIL_INCOMPATIBLE",
        "severity": "LOW",
        "summary": "Unity Connection pilot 9999 maps to Webex voicemail",
        "context": {"pilot": "9999", "vm_system": "CUC-Primary"},
        "options": [
            {"id": "webex_vm", "label": "Webex Voicemail", "impact": "Cloud voicemail"},
            {"id": "skip", "label": "Skip", "impact": "No voicemail migration"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0011",
        "type": "WORKSPACE_LICENSE_TIER",
        "severity": "LOW",
        "summary": "Conference room CR-A needs Professional license for call settings",
        "context": {"workspace_name": "CR-A", "required_tier": "Professional"},
        "options": [
            {"id": "professional", "label": "Professional", "impact": "Full settings"},
            {"id": "basic", "label": "Basic", "impact": "Limited settings"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0012",
        "type": "SHARED_LINE_COMPLEX",
        "severity": "MEDIUM",
        "summary": "DN 1001 appears on 4 devices with monitoring-only appearances",
        "context": {"dn": "1001", "device_count": 4, "monitoring_only": True},
        "options": [
            {"id": "virtual_line", "label": "Virtual line", "impact": "Shared appearance via virtual line"},
            {"id": "skip", "label": "Skip shared lines", "impact": "Primary only migrated"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0013",
        "type": "HOTDESK_DN_CONFLICT",
        "severity": "LOW",
        "summary": "Hot desk DN 5000 conflicts with user extension",
        "context": {"dn": "5000", "conflict_type": "user_extension"},
        "options": [
            {"id": "reassign", "label": "Reassign hotdesk DN", "impact": "New DN assigned"},
            {"id": "skip", "label": "Skip hotdesk", "impact": "Hotdesking not migrated"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0014",
        "type": "DEVICE_FIRMWARE_CONVERTIBLE",
        "severity": "LOW",
        "summary": "CP-8851 can be converted to MPP firmware",
        "context": {"model": "CP-8851", "count": 5},
        "options": [
            {"id": "convert", "label": "Convert firmware", "impact": "MPP firmware flash required"},
            {"id": "skip", "label": "Skip device", "impact": "Device not migrated"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0015",
        "type": "CALLING_PERMISSION_MISMATCH",
        "severity": "LOW",
        "summary": "Partition PT-LD has 0 assigned users",
        "context": {"partition": "PT-LD", "assigned_users_count": 0},
        "options": [
            {"id": "skip", "label": "Skip permission", "impact": "No calling permission created"},
            {"id": "create", "label": "Create permission", "impact": "Empty permission policy"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0016",
        "type": "LOCATION_AMBIGUOUS",
        "severity": "MEDIUM",
        "summary": "Device pools DP-HQ and DP-HQ-Phones share same region",
        "context": {"pools": ["DP-HQ", "DP-HQ-Phones"], "region": "US-West"},
        "options": [
            {"id": "consolidate", "label": "Single Webex location", "impact": "Both pools → HQ"},
            {"id": "separate", "label": "Two Webex locations", "impact": "Maintains pool separation"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0017",
        "type": "EXTENSION_CONFLICT",
        "severity": "HIGH",
        "summary": "Extension 2001 exists in both PT-Internal and PT-External",
        "context": {"extension": "2001", "partitions": ["PT-Internal", "PT-External"]},
        "options": [
            {"id": "keep_internal", "label": "Keep PT-Internal assignment", "impact": "PT-External dropped"},
            {"id": "skip", "label": "Skip extension", "impact": "Extension not migrated"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0018",
        "type": "DUPLICATE_USER",
        "severity": "MEDIUM",
        "summary": "john.doe@example.com exists in CUCM and Webex",
        "context": {"email": "john.doe@example.com"},
        "options": [
            {"id": "update", "label": "Update existing Webex user", "impact": "Settings merged"},
            {"id": "skip", "label": "Skip user", "impact": "CUCM settings not applied"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0019",
        "type": "AUDIO_ASSET_MANUAL",
        "severity": "LOW",
        "summary": "MOH audio file greeting.wav needs manual upload",
        "context": {"filename": "greeting.wav", "size_kb": 240},
        "options": [
            {"id": "manual", "label": "Upload manually", "impact": "Operator uploads to Webex"},
            {"id": "skip", "label": "Skip audio", "impact": "Default MOH used"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
    {
        "decision_id": "D0020",
        "type": "BUTTON_UNMAPPABLE",
        "severity": "LOW",
        "summary": "Button template BT-Executive has XML service buttons with no Webex equivalent",
        "context": {"template": "BT-Executive", "unmapped_count": 2},
        "options": [
            {"id": "skip_unmapped", "label": "Skip unmapped buttons", "impact": "Button slots left empty"},
            {"id": "skip_template", "label": "Skip entire template", "impact": "Default layout used"},
        ],
        "recommendation": None, "recommendation_reasoning": None,
    },
]


def _fingerprint(decision: dict) -> str:
    key = f"{decision['type']}:{json.dumps(decision['context'], sort_keys=True)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def build_fixture() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with MigrationStore(DB_PATH) as store:
        store.set_run_id("benchmark-run-001")
        for d in DECISIONS:
            record = {
                "decision_id": d["decision_id"],
                "type": d["type"],
                "severity": d["severity"],
                "summary": d["summary"],
                "context": d.get("context", {}),
                "options": d.get("options", []),
                "chosen_option": None,
                "resolved_at": None,
                "resolved_by": None,
                "fingerprint": _fingerprint(d),
                "run_id": "benchmark-run-001",
                "recommendation": d.get("recommendation"),
                "recommendation_reasoning": d.get("recommendation_reasoning"),
            }
            store.save_decision(record)

    print(f"Fixture built: {DB_PATH}")
    print(f"  {len(DECISIONS)} decisions written")


if __name__ == "__main__":
    build_fixture()
