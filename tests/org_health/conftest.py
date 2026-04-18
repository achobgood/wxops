import json
import pytest


REQUIRED_FILES = [
    "auto_attendants.json",
    "call_queues.json",
    "hunt_groups.json",
    "voicemail_groups.json",
    "paging_groups.json",
    "call_parks.json",
    "devices.json",
    "workspaces.json",
    "users.json",
    "dial_plans.json",
    "route_groups.json",
    "route_lists.json",
    "trunks.json",
    "numbers.json",
]


@pytest.fixture
def sample_manifest():
    return {
        "collected_at": "2026-04-17T14:30:00Z",
        "org_id": "org-abc-123",
        "org_name": "Acme Corp",
        "total_users": 50,
        "total_devices": 60,
        "sampled_users_for_permissions": 50,
        "commands_run": ["auto-attendant list", "call-queue list"],
        "wxcli_version": "0.1.0",
    }


@pytest.fixture
def collected_dir(tmp_path, sample_manifest):
    """Create a valid collected directory with all required files."""
    d = tmp_path / "collected"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(sample_manifest))
    for f in REQUIRED_FILES:
        (d / f).write_text(json.dumps([]))
    (d / "call_queue_details").mkdir()
    (d / "outgoing_permissions").mkdir()
    return d


@pytest.fixture
def sample_collected_data():
    """Minimal collected data dict for check tests."""
    return {
        "manifest": {
            "collected_at": "2026-04-17T14:30:00Z",
            "org_id": "org-abc-123",
            "org_name": "Acme Corp",
            "total_users": 50,
            "total_devices": 60,
            "sampled_users_for_permissions": 50,
        },
        "auto_attendants": [],
        "call_queues": [],
        "hunt_groups": [],
        "voicemail_groups": [],
        "paging_groups": [],
        "call_parks": [],
        "devices": [],
        "workspaces": [],
        "users": [],
        "dial_plans": [],
        "route_groups": [],
        "route_lists": [],
        "trunks": [],
        "numbers": [],
        "call_queue_details": {},
        "outgoing_permissions": {},
    }
