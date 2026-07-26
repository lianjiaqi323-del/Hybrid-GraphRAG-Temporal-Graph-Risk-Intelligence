"""Evidence-bounded deterministic and optional LLM generation."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .models import EvidenceBundle


def deterministic_explanation(bundle: EvidenceBundle) -> str:
    lines = [
        (
            "Assessment scope: structural association evidence available by "
            f"time step {bundle.query_time}."
        ),
        "",
    ]

    if bundle.supporting:
        for item in bundle.supporting:
            path = " -> ".join(item.payload["node_ids"])
            lines.append(
                f"Supporting path [{item.evidence_id}]: {path}. "
                "The endpoint had a historically known high-risk label by the "
                "query cutoff."
            )
    else:
        lines.append(
            "No time-valid path to a historically known high-risk endpoint was "
            "retrieved within the configured path budget."
        )

    if bundle.counter:
        lines.append("")
        for item in bundle.counter:
            path = " -> ".join(item.payload["node_ids"])
            lines.append(
                f"Counter-evidence path [{item.evidence_id}]: {path}. "
                "The endpoint had a historically known low-risk label by the "
                "query cutoff."
            )

    if bundle.analogues:
        lines.append("")
        for item in bundle.analogues:
            lines.append(
                f"Historical analogue [{item.evidence_id}]: "
                f"{item.payload['case_id']} was retrieved as a similar earlier "
                "case. Similarity is not a financial-transfer relationship."
            )

    exclusion = bundle.exclusions[0]
    lines.extend(
        [
            "",
            (
                f"Temporal audit [{exclusion.evidence_id}]: "
                f"{exclusion.payload['future_incident_edges_excluded']} incident "
                "future edge(s) were excluded."
            ),
            "",
            (
                "This output is decision support, not proof of criminal intent "
                "or causal risk transmission."
            ),
        ]
    )
    return "\n".join(lines)


def build_evidence_prompt(bundle: EvidenceBundle) -> str:
    evidence_json = json.dumps(bundle.to_dict(), indent=2, ensure_ascii=True)
    return f"""You are a financial-risk investigation assistant.

Answer the question using only the evidence bundle below.

Rules:
1. Cite evidence IDs in square brackets after every factual claim.
2. Preserve path direction and do not invent nodes, edges, amounts, or labels.
3. Distinguish graph-transfer paths from vector-similar historical cases.
4. Describe association, not proven causality or criminal intent.
5. State when the available evidence is insufficient.
6. Keep the answer under 250 words.

Question:
{bundle.question}

Validated evidence bundle:
{evidence_json}
"""


class OpenAICompatibleGenerator:
    """Small standard-library client for local or hosted compatible endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "OpenAICompatibleGenerator":
        base_url = os.environ.get("LLM_BASE_URL")
        model = os.environ.get("LLM_MODEL")
        if not base_url or not model:
            raise ValueError("LLM_BASE_URL and LLM_MODEL must be configured.")
        return cls(
            base_url=base_url,
            model=model,
            api_key=os.environ.get("LLM_API_KEY", "local"),
        )

    def generate(self, bundle: EvidenceBundle) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": build_evidence_prompt(bundle)}
            ],
            "temperature": 0,
            "max_tokens": 450,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        try:
            answer = str(result["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM response does not contain message content.") from exc

        errors = validate_generated_citations(answer, bundle)
        if errors:
            raise RuntimeError("LLM citation validation failed: " + "; ".join(errors))
        return answer


def validate_generated_citations(answer: str, bundle: EvidenceBundle) -> list[str]:
    known = {item.evidence_id for item in bundle.all_items}
    cited = set(re.findall(r"\[([A-Z][A-Z0-9-]*\d{3})\]", answer))
    errors: list[str] = []
    unknown = cited - known
    if unknown:
        errors.append(f"unknown evidence IDs: {sorted(unknown)}")
    if bundle.all_items and not cited:
        errors.append("answer contains no evidence citations")
    return errors

