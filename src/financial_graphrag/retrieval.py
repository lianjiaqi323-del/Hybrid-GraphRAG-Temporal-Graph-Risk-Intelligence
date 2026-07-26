"""Query-driven temporal graph-path retrieval."""

from __future__ import annotations

import math
from collections import deque

from .graph_store import TemporalGraph
from .models import PathResult


class TemporalPathRetriever:
    """Retrieve short, time-valid paths to historically labelled endpoints."""

    def __init__(self, graph: TemporalGraph) -> None:
        self.graph = graph

    def retrieve(
        self,
        source: str,
        query_time: int,
        *,
        target_label: str,
        max_edges: int = 4,
        top_k: int = 3,
        direction: str = "outgoing",
    ) -> list[PathResult]:
        if source not in self.graph.nodes:
            raise KeyError(f"Unknown source node: {source}")
        if target_label not in {"high_risk", "low_risk"}:
            raise ValueError("target_label must be high_risk or low_risk")
        if max_edges < 1:
            raise ValueError("max_edges must be positive")

        queue = deque([(source, (source,), tuple(), 0.0, 0)])
        results: list[PathResult] = []

        while queue:
            current, node_path, edge_path, total_amount, latest_time = queue.popleft()
            if len(edge_path) >= max_edges:
                continue

            for edge in self.graph.visible_edges(current, query_time, direction):
                if direction == "incoming":
                    next_node = edge.source
                elif direction == "outgoing":
                    next_node = edge.target
                else:
                    next_node = edge.target if edge.source == current else edge.source

                if next_node in node_path:
                    continue

                next_nodes = node_path + (next_node,)
                next_edges = edge_path + (edge.edge_id,)
                next_amount = total_amount + edge.amount
                next_latest = max(latest_time, edge.observed_time)
                known_label = self.graph.nodes[next_node].known_label_at(query_time)

                if known_label == target_label and next_node != source:
                    results.append(
                        PathResult(
                            node_ids=next_nodes,
                            edge_ids=next_edges,
                            endpoint_label=known_label,
                            score=self._score_path(
                                query_time=query_time,
                                latest_time=next_latest,
                                edge_count=len(next_edges),
                                total_amount=next_amount,
                            ),
                            observed_time_max=next_latest,
                            total_amount=next_amount,
                            direction=direction,
                        )
                    )

                queue.append(
                    (next_node, next_nodes, next_edges, next_amount, next_latest)
                )

        results.sort(
            key=lambda path: (
                -path.score,
                len(path.edge_ids),
                path.node_ids,
            )
        )
        return results[:top_k]

    @staticmethod
    def _score_path(
        *, query_time: int, latest_time: int, edge_count: int, total_amount: float
    ) -> float:
        """Transparent ranking heuristic for the synthetic public demo."""

        age = max(0, query_time - latest_time)
        recency = 1.0 / (1.0 + age)
        amount_signal = math.log1p(total_amount) / 10.0
        compactness = 1.0 / edge_count
        return round(0.50 * recency + 0.30 * compactness + 0.20 * amount_signal, 6)

