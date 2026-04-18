from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Finding:
    check_name: str
    category: str
    severity: str
    title: str
    detail: str
    affected_items: list[dict]
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CategoryScore:
    category: str
    display_name: str
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    findings: list[Finding]

    @classmethod
    def from_findings(cls, category: str, display_name: str, findings: list[Finding]) -> CategoryScore:
        return cls(
            category=category,
            display_name=display_name,
            high_count=sum(1 for f in findings if f.severity == "HIGH"),
            medium_count=sum(1 for f in findings if f.severity == "MEDIUM"),
            low_count=sum(1 for f in findings if f.severity == "LOW"),
            info_count=sum(1 for f in findings if f.severity == "INFO"),
            findings=findings,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d


@dataclass
class OrgStats:
    total_users: int
    total_devices: int
    total_auto_attendants: int
    total_call_queues: int
    total_hunt_groups: int
    total_trunks: int
    total_locations: int
    sampled_users_for_permissions: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HealthResult:
    org_name: str
    org_id: str
    collected_at: str
    categories: dict[str, CategoryScore]
    findings: list[Finding]
    stats: OrgStats

    def to_dict(self) -> dict:
        return {
            "org_name": self.org_name,
            "org_id": self.org_id,
            "collected_at": self.collected_at,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats.to_dict(),
        }
