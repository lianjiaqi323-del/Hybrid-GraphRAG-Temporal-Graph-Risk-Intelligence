"""Build and validate auditable evidence bundles."""

from __future__ import annotations

from collections.abc import Iterable

from .graph_store import TemporalGraph
from .models import AnalogueResult, EvidenceBundle, EvidenceItem, PathResult


def build_evidence_bundle(
    *,
    graph: TemporalGraph,
    query_entity: str,
    query_time: int,
    question: str,
    supporting_paths: list[PathResult],
    counter_paths: list[PathResult],
    analogues: list[AnalogueResult],
) -> EvidenceBundle:
    supporting = tuple(
        _path_item(graph, path, f"G-PATH-{index:03d}", "supporting_path")
        for index, path in enumerate(supporting_paths, start=1)
    )
    counter = tuple(
        _path_item(graph, path, f"G-COUNTER-{index:03d}", "counter_path")
        for index, path in enumerate(counter_paths, start=1)
    )
    analogue_items = tuple(
        EvidenceItem(
            evidence_id=f"V-CASE-{index:03d}",
            evidence_type="historical_analogue",
            observed_time=result.observed_time,
            temporally_valid=result.observed_time <= query_time,
            provenance="synthetic historical-case index",
            payload={
                "case_id": result.case_id,
                "historical_label": result.label,
                "similarity": result.similarity,
                "summary": result.summary,
                "relation_semantics": "similarity_not_financial_transfer",
            },
        )
        for index, result in enumerate(analogues, start=1)
    )

    future_count = graph.excluded_future_edge_count(query_entity, query_time)
    exclusions = (
        EvidenceItem(
            evidence_id="X-TIME-001",
            evidence_type="exclusion_notice",
            observed_time=query_time,
            temporally_valid=True,
            provenance="temporal retrieval policy",
            payload={
                "future_incident_edges_excluded": future_count,
                "rule": "edge.observed_time <= query_time",
            },
        ),
    )

    bundle = EvidenceBundle(
        query_entity=query_entity,
        query_time=query_time,
        question=question,
        supporting=supporting,
        counter=counter,
        analogues=analogue_items,
        exclusions=exclusions,
    )
    errors = validate_evidence_bundle(bundle)
    if errors:
        raise ValueError("Invalid evidence bundle: " + "; ".join(errors))
    return bundle


def _path_item(
    graph: TemporalGraph,
    path: PathResult,
    evidence_id: str,
    evidence_type: str,
) -> EvidenceItem:
    edge_details = []
    for edge_id in path.edge_ids:
        edge = graph.edges[edge_id]
        edge_details.append(
            {
                "edge_id": edge.edge_id,
                "source": edge.source,
                "target": edge.target,
                "relation": edge.relation,
                "observed_time": edge.observed_time,
                "amount": edge.amount,
                "currency": edge.currency,
            }
        )
    endpoint = graph.nodes[path.node_ids[-1]]
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        observed_time=path.observed_time_max,
        temporally_valid=True,
        provenance="synthetic typed temporal graph",
        payload={
            "node_ids": list(path.node_ids),
            "edges": edge_details,
            "endpoint_label": path.endpoint_label,
            "endpoint_label_available_time": endpoint.label_available_time,
            "path_score": path.score,
            "total_amount": path.total_amount,
            "direction": path.direction,
        },
    )


def validate_evidence_bundle(bundle: EvidenceBundle) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()

    for item in bundle.all_items:
        prefix = item.evidence_id
        if item.evidence_id in seen:
            errors.append(f"{prefix}: duplicate evidence ID")
        seen.add(item.evidence_id)
        if item.temporally_valid and item.observed_time is None:
            errors.append(f"{prefix}: temporally valid evidence has no observation time")
        if item.observed_time is not None and item.observed_time > bundle.query_time:
            errors.append(
                f"{prefix}: future evidence {item.observed_time} > {bundle.query_time}"
            )
        if item.evidence_type == "historical_analogue":
            if item.payload.get("relation_semantics") != "similarity_not_financial_transfer":
                errors.append(f"{prefix}: vector similarity is misrepresented as an edge")

    errors.extend(_validate_path_group(bundle.supporting, expected_label="high_risk"))
    errors.extend(_validate_path_group(bundle.counter, expected_label="low_risk"))
    return errors


def _validate_path_group(
    items: Iterable[EvidenceItem], *, expected_label: str
) -> list[str]:
    errors: list[str] = []
    for item in items:
        if item.payload.get("endpoint_label") != expected_label:
            errors.append(
                f"{item.evidence_id}: expected endpoint label {expected_label}"
            )
        nodes = item.payload.get("node_ids", [])
        edges = item.payload.get("edges", [])
        if len(nodes) != len(edges) + 1:
            errors.append(f"{item.evidence_id}: broken path closure")
        for left, edge, right in zip(nodes[:-1], edges, nodes[1:], strict=True):
            if edge.get("source") != left or edge.get("target") != right:
                errors.append(f"{item.evidence_id}: path direction mismatch")
    return errors
