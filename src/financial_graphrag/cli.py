"""Command-line entry point for the synthetic public demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .graph_store import TemporalGraph
from .pipeline import FinancialRiskPipeline
from .vector_retrieval import HistoricalCaseRetriever


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_demo_pipeline() -> FinancialRiskPipeline:
    root = repository_root()
    graph = TemporalGraph.from_json(root / "examples" / "synthetic_graph.json")
    cases = HistoricalCaseRetriever.from_json(
        root / "examples" / "historical_cases.json"
    )
    return FinancialRiskPipeline(graph, cases)


def run_demo(*, use_llm: bool, as_json: bool) -> int:
    pipeline = build_demo_pipeline()
    result = pipeline.investigate(
        wallet_id="wallet_query",
        query_time=8,
        question=(
            "Which time-valid fund-flow paths connect wallet_query to "
            "historically known high-risk entities, and what counter-evidence "
            "is available?"
        ),
        use_llm=use_llm,
    )
    if as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=True))
    else:
        print(result.answer)
        print(f"\nGeneration mode: {result.generation_mode}")
        if result.generation_warning:
            print(f"Generation warning: {result.generation_warning}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="financial-graphrag",
        description="Run the portfolio-safe financial GraphRAG demonstration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Run the synthetic evidence demo.")
    demo.add_argument(
        "--use-llm",
        action="store_true",
        help="Use an OpenAI-compatible endpoint, with deterministic fallback.",
    )
    demo.add_argument(
        "--json",
        action="store_true",
        help="Print the complete evidence bundle as JSON.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "demo":
        return run_demo(use_llm=args.use_llm, as_json=args.json)
    raise AssertionError("Unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())

