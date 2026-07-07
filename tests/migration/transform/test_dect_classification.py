"""Tests for DECT phone model classification."""

from wxcli.migration.models import DeviceCompatibilityTier
from wxcli.migration.transform.cross_reference import classify_phone_model


class TestDECTEnum:
    def test_dect_tier_exists(self):
        """DECT is a valid DeviceCompatibilityTier value."""
        assert DeviceCompatibilityTier.DECT == "dect"

    def test_dect_tier_is_distinct(self):
        """DECT is not the same as any other tier."""
        assert DeviceCompatibilityTier.DECT != DeviceCompatibilityTier.NATIVE_MPP
        assert DeviceCompatibilityTier.DECT != DeviceCompatibilityTier.INCOMPATIBLE


class TestDECTClassification:
    """DECT model string recognition."""

    def test_cisco_6823(self):
        assert classify_phone_model("Cisco 6823") == DeviceCompatibilityTier.DECT

    def test_cisco_6825(self):
        assert classify_phone_model("Cisco 6825") == DeviceCompatibilityTier.DECT

    def test_cisco_6825ip(self):
        assert classify_phone_model("Cisco 6825ip") == DeviceCompatibilityTier.DECT

    def test_cisco_ip_phone_6823(self):
        assert classify_phone_model("Cisco IP Phone 6823") == DeviceCompatibilityTier.DECT

    def test_cisco_ip_phone_6825(self):
        assert classify_phone_model("Cisco IP Phone 6825") == DeviceCompatibilityTier.DECT

    def test_cisco_ip_phone_6825ip(self):
        assert classify_phone_model("Cisco IP Phone 6825ip") == DeviceCompatibilityTier.DECT


class TestDECTDoesNotMatchDeskPhones:
    """6821/6841/6851 are desk phones, NOT DECT — must stay NATIVE_MPP."""

    def test_6821_is_native_mpp(self):
        assert classify_phone_model("Cisco 6821") == DeviceCompatibilityTier.NATIVE_MPP

    def test_6841_is_native_mpp(self):
        assert classify_phone_model("Cisco 6841") == DeviceCompatibilityTier.NATIVE_MPP

    def test_6851_is_native_mpp(self):
        assert classify_phone_model("Cisco 6851") == DeviceCompatibilityTier.NATIVE_MPP

    def test_6861_is_native_mpp(self):
        assert classify_phone_model("Cisco 6861") == DeviceCompatibilityTier.NATIVE_MPP
