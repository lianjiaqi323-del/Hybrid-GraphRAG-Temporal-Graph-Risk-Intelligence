"""In-memory typed temporal graph used by the public demonstration."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .models import Edge, Node


class TemporalGraph:
    """A small directed graph with explicit observation-time semantics."""

    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        self.edges = {edge.edge_id: edge for edge in edges}
        self.outgoing: dict[str, list[str]] = defaultdict(list)
        self.incoming: dict[str, list[str]] = defaultdict(list)
        self._validate_and_index()

    @classmethod
    def from_json(cls, path: str | Path) -> "TemporalGraph":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = [
            Node(
                node_id=str(item["node_id"]),
                node_type=item["node_type"],
                label=item.get("label", "unknown"),
                label_available_time=item.get("label_available_time"),
                attributes=dict(item.get("attributes", {})),
            )
            for item in raw["nodes"]
        ]
        edges = [
            Edge(
                edge_id=str(item["edge_id"]),
                source=str(item["source"]),
                target=str(item["target"]),
                relation=str(item["relation"]),
                observed_time=int(item["observed_time"]),
                amount=float(item.get("amount", 0.0)),
                currency=str(item.get("currency", "SYNTH")),
            )
            for item in raw["edges"]
        ]
        return cls(nodes, edges)

    def _validate_and_index(self) -> None:
        if len(self.nodes) == 0:
            raise ValueError("The graph must contain at least one node.")
        if len(self.edges) == 0:
            raise ValueError("The graph must contain at least one edge.")

        for edge in self.edges.values():
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"Edge {edge.edge_id} references an unknown node.")
            if edge.observed_time < 0:
                raise ValueError(f"Edge {edge.edge_id} has a negative observation time.")
            if edge.amount < 0:
                raise ValueError(f"Edge {edge.edge_id} has a negative amount.")
            self.outgoing[edge.source].append(edge.edge_id)
            self.incoming[edge.target].append(edge.edge_id)

    def visible_edges(self, node_id: str, query_time: int, direction: str) -> list[Edge]:
        """Return edges visible by ``query_time`` while preserving direction."""

        if node_id not in self.nodes:
            raise KeyError(f"Unknown node: {node_id}")
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError("direction must be outgoing, incoming, or both")

        edge_ids: list[str] = []
        if direction in {"outgoing", "both"}:
            edge_ids.extend(self.outgoing.get(node_id, []))
        if direction in {"incoming", "both"}:
            edge_ids.extend(self.incoming.get(node_id, []))
        return sorted(
            (self.edges[edge_id] for edge_id in set(edge_ids)
             if self.edges[edge_id].observed_time <= query_time),
            key=lambda edge: (edge.observed_time, edge.edge_id),
        )

    def excluded_future_edge_count(self, node_id: str, query_time: int) -> int:
        incident = set(self.outgoing.get(node_id, [])) | set(self.incoming.get(node_id, []))
        return sum(self.edges[edge_id].observed_time > query_time for edge_id in incident)

