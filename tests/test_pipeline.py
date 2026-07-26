from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from financial_graphrag.evidence import validate_evidence_bundle
from financial_graphrag.generation import validate_generated_citations
from financial_graphrag.graph_store import TemporalGraph
from financial_graphrag.models import EvidenceBundle, EvidenceItem
from financial_graphrag.pipeline import FinancialRiskPipeline
from financial_graphrag.retrieval import TemporalPathRetriever
from financial_graphrag.vector_retrieval import HistoricalCaseRetriever


ROOT = Path(__file__).resolve().parents[1]


class GraphRAGPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = TemporalGraph.from_json(ROOT / "examples" / "synthetic_graph.json")
        cls.cases = HistoricalCaseRetriever.from_json(
            ROOT / "examples" / "historical_cases.json"
        )
        cls.paths = TemporalPathRetriever(cls.graph)
        cls.pipeline = FinancialRiskPipeline(cls.graph, cls.cases)

    def test_future_edges_are_not_visible(self) -> None:
        visible_ids = {
            edge.edge_id
            for edge in self.graph.visible_edges("wallet_query", 8, "outgoing")
        }
        self.assertNotIn("edge_007", visible_ids)
        self.assertEqual(self.graph.excluded_future_edge_count("wallet_query", 8), 1)

    def test_supporting_paths_are_directed_and_time_valid(self) -> None:
        paths = self.paths.retrieve(
            "wallet_query", 8, target_label="high_risk", max_edges=4, top_k=5
        )
        self.assertEqual(len(paths), 2)
        for path in paths:
            self.assertEqual(path.node_ids[0], "wallet_query")
            self.assertEqual(path.node_ids[-1], "wallet_watchlist")
            self.assertLessEqual(path.observed_time_max, 8)
            self.assertEqual(path.endpoint_label, "high_risk")

    def test_future_endpoint_label_is_not_available_early(self) -> None:
        at_nine = self.paths.retrieve(
            "wallet_query", 9, target_label="high_risk", max_edges=2, top_k=5
        )
        self.assertFalse(
            any(path.node_ids[-1] == "wallet_future_watchlist" for path in at_nine)
        )
        at_ten = self.paths.retrieve(
            "wallet_query", 10, target_label="high_risk", max_edges=2, top_k=5
        )
        self.assertTrue(
            any(path.node_ids[-1] == "wallet_future_watchlist" for path in at_ten)
        )

    def test_low_risk_path_is_counter_evidence(self) -> None:
        paths = self.paths.retrieve(
            "wallet_query", 8, target_label="low_risk", max_edges=4, top_k=5
        )
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].node_ids[-1], "wallet_merchant")

    def test_vector_retrieval_excludes_future_cases(self) -> None:
        query = self.graph.nodes["wallet_query"].attributes["risk_features"]
        results = self.cases.retrieve(query, 8, top_k=10)
        self.assertNotIn("case_future", {result.case_id for result in results})
        self.assertEqual(results[0].case_id, "case_risky_02")

    def test_pipeline_returns_valid_cited_explanation(self) -> None:
        result = self.pipeline.investigate(
            wallet_id="wallet_query",
            query_time=8,
            question="Show the time-valid supporting and counter-evidence.",
        )
        self.assertEqual(result.generation_mode, "deterministic")
        self.assertFalse(validate_evidence_bundle(result.evidence))
        self.assertFalse(validate_generated_citations(result.answer, result.evidence))
        self.assertIn("not proof of criminal intent", result.answer)

    def test_missing_llm_configuration_fails_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = self.pipeline.investigate(
                wallet_id="wallet_query",
                query_time=8,
                question="Explain the retrieved evidence.",
                use_llm=True,
            )
        self.assertEqual(result.generation_mode, "deterministic_fallback")
        self.assertIn("LLM_BASE_URL", result.generation_warning or "")

    def test_future_evidence_is_rejected(self) -> None:
        future_item = EvidenceItem(
            evidence_id="X-FUTURE-001",
            evidence_type="exclusion_notice",
            observed_time=9,
            temporally_valid=True,
            provenance="unit test",
            payload={},
        )
        bundle = EvidenceBundle(
            query_entity="wallet_query",
            query_time=8,
            question="test",
            supporting=(),
            counter=(),
            analogues=(),
            exclusions=(future_item,),
        )
        errors = validate_evidence_bundle(bundle)
        self.assertTrue(any("future evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

