from wxcli.migration.models import DecisionType

def test_device_settings_lossy_exists():
    assert DecisionType.DEVICE_SETTINGS_LOSSY == "DEVICE_SETTINGS_LOSSY"
    assert DecisionType.DEVICE_SETTINGS_LOSSY.value == "DEVICE_SETTINGS_LOSSY"
