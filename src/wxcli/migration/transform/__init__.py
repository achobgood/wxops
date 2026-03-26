"""Migration transform package — normalization and cross-reference building.

Pass 1 (normalizers): Stateless pure functions, one CUCM dict → one canonical model.
Pass 2 (CrossReferenceBuilder): Builds cross-ref indexes using full SQLite inventory.
Pipeline (normalize_discovery): Entry point connecting DiscoveryResult → store.
"""

from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY
from wxcli.migration.transform.pipeline import normalize_discovery

__all__ = ["CrossReferenceBuilder", "NORMALIZER_REGISTRY", "normalize_discovery"]
