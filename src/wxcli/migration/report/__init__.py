"""CUCM migration assessment report package."""

from wxcli.migration.report.ingest import ingest_collector_file
from wxcli.migration.report.assembler import assemble_report

__all__ = ["ingest_collector_file", "assemble_report"]
