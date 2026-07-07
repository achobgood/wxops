"""Tests for collector file ingestion."""

import gzip
import json

import pytest


class TestIngestCollectorFile:
    """Ingestion of .json.gz and .json collector files."""

    def test_ingest_collector_file_reads_gzip(self, sample_collector_file):
        from wxcli.migration.report.ingest import ingest_collector_file

        result, metadata = ingest_collector_file(sample_collector_file)
        assert isinstance(result, dict)
        # Must have top-level extractor groups
        assert "locations" in result
        assert "users" in result
        assert "devices" in result
        assert "routing" in result
        assert "features" in result
        assert "voicemail" in result
        # Metadata should contain collector header fields
        assert metadata["cucm_version"] == "14.0.1.13900-155"
        assert metadata["cluster_name"] == "CUCM-LAB"
        assert metadata["collector_version"] == "1.0"
        assert metadata["collected_at"] == "2026-03-24T12:00:00Z"

    def test_ingest_collector_file_reads_plain_json(self, tmp_path):
        from wxcli.migration.report.ingest import ingest_collector_file

        collector_data = {
            "collector_version": "1.0",
            "cucm_version": "14.0",
            "cluster_name": "TEST",
            "collected_at": "2026-03-24T12:00:00Z",
            "objects": {
                "phone": [{"name": "SEP001122334455", "model": "Cisco 8845"}],
                "endUser": [],
                "devicePool": [],
                "routePartition": [],
                "css": [],
                "huntPilot": [],
                "huntList": [],
                "lineGroup": [],
                "ctiRoutePoint": [],
                "callPark": [],
                "callPickupGroup": [],
                "routePattern": [],
                "gateway": [],
                "sipTrunk": [],
                "routeGroup": [],
                "routeList": [],
                "transPattern": [],
                "timeSchedule": [],
                "timePeriod": [],
                "voicemailProfile": [],
                "voicemailPilot": [],
            },
        }
        file_path = tmp_path / "collector.json"
        file_path.write_text(json.dumps(collector_data))

        result, metadata = ingest_collector_file(file_path)
        assert isinstance(result, dict)
        assert "devices" in result
        assert len(result["devices"]["phones"]) == 1
        assert metadata["cucm_version"] == "14.0"
        assert metadata["cluster_name"] == "TEST"

    def test_ingest_collector_file_rejects_invalid(self, tmp_path):
        from wxcli.migration.report.ingest import ingest_collector_file

        bad_data = {"some_key": "some_value"}
        file_path = tmp_path / "bad.json"
        file_path.write_text(json.dumps(bad_data))

        with pytest.raises(ValueError, match="collector_version"):
            ingest_collector_file(file_path)

    def test_collector_to_raw_data_mapping(self, sample_collector_file):
        """Verify key mappings match discovery.py raw_data contract."""
        from wxcli.migration.report.ingest import ingest_collector_file

        result, _metadata = ingest_collector_file(sample_collector_file)

        # locations group: device_pools, datetime_groups, cucm_locations
        assert "device_pools" in result["locations"]
        assert "datetime_groups" in result["locations"]
        assert "cucm_locations" in result["locations"]

        # users group: users
        assert "users" in result["users"]

        # devices group: phones
        assert "phones" in result["devices"]

        # routing group keys
        routing = result["routing"]
        for key in ["partitions", "css_list", "route_patterns", "gateways",
                     "sip_trunks", "route_groups", "route_lists",
                     "translation_patterns"]:
            assert key in routing, f"Missing routing key: {key}"

        # features group keys
        features = result["features"]
        for key in ["hunt_pilots", "hunt_lists", "line_groups",
                     "cti_route_points", "call_parks", "pickup_groups",
                     "time_schedules", "time_periods"]:
            assert key in features, f"Missing features key: {key}"

        # voicemail group keys
        voicemail = result["voicemail"]
        assert "voicemail_profiles" in voicemail
        assert "voicemail_pilots" in voicemail
