"""End-to-end orchestration for the public GraphRAG demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import build_evidence_bundle
from .generation import OpenAICompatibleGenerator, deterministic_explanation
from .graph_store import TemporalGraph
from .models import EvidenceBundle
from .retrieval import TemporalPathRetriever
from .vector_retrieval import HistoricalCaseRetriever


@dataclass(frozen=True)
class PipelineResult:
    evidence: EvidenceBundle
    answer: str
    generation_mode: str
    generation_warning: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_mode": self.generation_mode,
            "generation_warning": self.generation_warning,
            "answer": self.answer,
            "evidence": self.evidence.to_dict(),
        }


class FinancialRiskPipeline:
    def __init__(
        self,
        graph: TemporalGraph,
        case_retriever: HistoricalCaseRetriever,
    ) -> None:
        self.graph = graph
        self.case_retriever = case_retriever
        self.path_retriever = TemporalPathRetriever(graph)

    def investigate(
        self,
        *,
        wallet_id: str,
        query_time: int,
        question: str,
        use_llm: bool = False,
        max_edges: int = 4,
        top_k_paths: int = 3,
        top_k_cases: int = 2,
    ) -> PipelineResult:
        wallet = self.graph.nodes.get(wallet_id)
        if wallet is None or wallet.node_type != "wallet":
            raise ValueError(f"Query entity must be a known wallet: {wallet_id}")

        supporting = self.path_retriever.retrieve(
            wallet_id,
            query_time,
            target_label="high_risk",
            max_edges=max_edges,
            top_k=top_k_paths,
        )
        counter = self.path_retriever.retrieve(
            wallet_id,
            query_time,
            target_label="low_risk",
            max_edges=max_edges,
            top_k=top_k_paths,
        )
        query_features = {
            key: float(value)
            for key, value in wallet.attributes.get("risk_features", {}).items()
        }
        analogues = self.case_retriever.retrieve(
            query_features, query_time, top_k=top_k_cases
        )
        bundle = build_evidence_bundle(
            graph=self.graph,
            query_entity=wallet_id,
            query_time=query_time,
            question=question,
            supporting_paths=supporting,
            counter_paths=counter,
            analogues=analogues,
        )

        if not use_llm:
            return PipelineResult(
                evidence=bundle,
                answer=deterministic_explanation(bundle),
                generation_mode="deterministic",
                generation_warning=None,
            )

        try:
            answer = OpenAICompatibleGenerator.from_environment().generate(bundle)
            return PipelineResult(
                evidence=bundle,
                answer=answer,
                generation_mode="openai_compatible_llm",
                generation_warning=None,
            )
        except (RuntimeError, ValueError) as exc:
            return PipelineResult(
                evidence=bundle,
                answer=deterministic_explanation(bundle),
                generation_mode="deterministic_fallback",
                generation_warning=str(exc),
            )

