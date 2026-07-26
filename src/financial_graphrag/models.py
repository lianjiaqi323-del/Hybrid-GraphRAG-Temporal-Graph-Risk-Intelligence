"""Typed records shared by graph retrieval, evidence validation, and generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RiskLabel = Literal["high_risk", "low_risk", "unknown"]
NodeType = Literal["wallet", "transaction"]


@dataclass(frozen=True)
class Node:
    node_id: str
    node_type: NodeType
    label: RiskLabel = "unknown"
    label_available_time: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def known_label_at(self, query_time: int) -> RiskLabel:
        """Return a label only when it was available by the query cutoff."""

        if self.label == "unknown" or self.label_available_time is None:
            return "unknown"
        if self.label_available_time > query_time:
            return "unknown"
        return self.label


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    relation: str
    observed_time: int
    amount: float
    currency: str = "SYNTH"


@dataclass(frozen=True)
class PathResult:
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    endpoint_label: RiskLabel
    score: float
    observed_time_max: int
    total_amount: float
    direction: str = "outgoing"


@dataclass(frozen=True)
class HistoricalCase:
    case_id: str
    observed_time: int
    label: RiskLabel
    features: dict[str, float]
    summary: str


@dataclass(frozen=True)
class AnalogueResult:
    case_id: str
    observed_time: int
    label: RiskLabel
    similarity: float
    summary: str


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    evidence_type: str
    observed_time: int | None
    temporally_valid: bool
    provenance: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["schema_version"] = "1.0"
        return record


@dataclass(frozen=True)
class EvidenceBundle:
    query_entity: str
    query_time: int
    question: str
    supporting: tuple[EvidenceItem, ...]
    counter: tuple[EvidenceItem, ...]
    analogues: tuple[EvidenceItem, ...]
    exclusions: tuple[EvidenceItem, ...]

    @property
    def all_items(self) -> tuple[EvidenceItem, ...]:
        return self.supporting + self.counter + self.analogues + self.exclusions

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "query_entity": self.query_entity,
            "query_time": self.query_time,
            "question": self.question,
            "supporting": [item.to_dict() for item in self.supporting],
            "counter": [item.to_dict() for item in self.counter],
            "analogues": [item.to_dict() for item in self.analogues],
            "exclusions": [item.to_dict() for item in self.exclusions],
        }

