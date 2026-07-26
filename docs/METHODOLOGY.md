# Methodology

## Research question

The prototype studies whether a financial-risk assistant can return compact,
time-valid, and auditable graph evidence for a queried wallet, then generate an
explanation that remains faithful to that evidence.

The public demo does **not** evaluate whether a wallet is truly illicit. It
tests the engineering contract around retrieval and explanation.

## Query protocol

Each query specifies:

1. a wallet identifier;
2. a query-time cutoff;
3. a risk-investigation question;
4. a maximum path length;
5. path and historical-case budgets.

The system never reads graph edges, historical cases, or endpoint labels that
became available after the cutoff.

## Evidence roles

### Supporting graph evidence

A directed, time-valid path ending at an entity with a historically available
`high_risk` label. Such a path establishes structural association only.

### Counter-evidence

A directed, time-valid path ending at an entity with a historically available
`low_risk` label. Counter-evidence is shown to prevent one-sided explanations.

### Historical analogue

An earlier case retrieved through numeric similarity. It is evidence about
precedent, not graph connectivity.

### Exclusion notice

A machine-readable record of information rejected by the temporal policy.

## Evaluation plan

The full research programme separates three evaluation layers.

### Prediction

- Average Precision (AP)
- precision, recall, F1, and F2
- Matthews Correlation Coefficient (MCC)
- AUROC for literature comparability
- calibration and fixed-budget investigation yield

### Retrieval

- path validity and direction correctness
- temporal validity
- endpoint-label availability
- evidence coverage and redundancy
- retrieval latency
- analyst relevance

### Generation

- citation validity
- numerical consistency
- unsupported-claim rate
- completeness and abstention quality
- expert-rated usefulness and clarity
- latency and token use

The public repository includes only synthetic functional tests. Dissertation
benchmarks and results are deliberately withheld.

## Scientific boundaries

- A historical risk label is incomplete forensic annotation, not judicial
  truth.
- A graph path is association evidence, not proof of criminal intent.
- Edge-removal sensitivity is not automatically a causal effect.
- Risk diffusion produced by a future GNN must be described as learned
  relation-aware inference unless causal assumptions are independently
  justified.
- Retrieval and prediction must be compared on frozen, leakage-safe protocols.

## Planned research extensions

- community-aware GraphRAG with diversity and path-closure budgets;
- GNN-based relation-aware risk inference inside query communities;
- joint GraphRAG, VectorRAG, and GNN evidence reconciliation;
- analyst-blinded explanation evaluation;
- robustness under temporal distribution shift.

