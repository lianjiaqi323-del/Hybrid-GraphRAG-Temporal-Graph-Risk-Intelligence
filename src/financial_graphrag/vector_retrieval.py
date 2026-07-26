"""Historical-case retrieval kept separate from financial graph edges."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .models import AnalogueResult, HistoricalCase


class HistoricalCaseRetriever:
    def __init__(self, cases: list[HistoricalCase]) -> None:
        self.cases = cases

    @classmethod
    def from_json(cls, path: str | Path) -> "HistoricalCaseRetriever":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        cases = [
            HistoricalCase(
                case_id=str(item["case_id"]),
                observed_time=int(item["observed_time"]),
                label=item.get("label", "unknown"),
                features={key: float(value) for key, value in item["features"].items()},
                summary=str(item["summary"]),
            )
            for item in raw["cases"]
        ]
        return cls(cases)

    def retrieve(
        self,
        query_features: dict[str, float],
        query_time: int,
        *,
        top_k: int = 3,
    ) -> list[AnalogueResult]:
        results: list[AnalogueResult] = []
        for case in self.cases:
            if case.observed_time > query_time:
                continue
            similarity = self._cosine(query_features, case.features)
            results.append(
                AnalogueResult(
                    case_id=case.case_id,
                    observed_time=case.observed_time,
                    label=case.label,
                    similarity=round(similarity, 6),
                    summary=case.summary,
                )
            )
        results.sort(key=lambda item: (-item.similarity, item.case_id))
        return results[:top_k]

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        keys = sorted(set(left) | set(right))
        a = [float(left.get(key, 0.0)) for key in keys]
        b = [float(right.get(key, 0.0)) for key in keys]
        denominator = math.sqrt(sum(value * value for value in a)) * math.sqrt(
            sum(value * value for value in b)
        )
        if denominator == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b, strict=True)) / denominator

