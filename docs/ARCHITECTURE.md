# System Architecture

## Design objective

The prototype separates risk estimation, retrieval, and explanation so that
each component can be tested independently.

```text
question
  -> deterministic router
  -> temporal graph-path retrieval
  -> historical case retrieval
  -> evidence contract
  -> evidence validation
  -> deterministic or LLM generation
  -> citation validation
```

## 1. Typed temporal graph

The graph contains two node types:

- `wallet`
- `transaction`

It contains two directed relation types:

- `wallet -[inputs_to]-> transaction`
- `transaction -[outputs_to]-> wallet`

Every edge has an `observed_time`. A query at cutoff \(t_q\) may use an edge
only when:

\[
t_e \leq t_q.
\]

A historical endpoint label may be used only when its availability time also
satisfies:

\[
t_{\text{label}} \leq t_q.
\]

These rules make temporal eligibility explicit and testable.

## 2. GraphRAG path retriever

The retriever performs bounded breadth-first search over visible directed
edges. It:

- prevents cycles within an individual path;
- preserves original direction and relation type;
- enforces an edge budget;
- retrieves high-risk and low-risk endpoints separately;
- ranks valid paths with a transparent heuristic combining recency,
  compactness, and amount.

In the wallet-transaction bipartite graph, one wallet-to-wallet transfer spans
two typed edges. A four-edge path therefore corresponds to two wallet-level
transfer hops.

The public scoring rule is intentionally simple and interpretable. It is a
demonstration of retrieval mechanics, not a trained risk model.

## 3. VectorRAG historical-case retriever

The case retriever uses cosine similarity over synthetic numeric profiles.
Only cases observed by the query cutoff are eligible.

Similarity records use the explicit semantic marker:

```text
similarity_not_financial_transfer
```

This prevents a common category error: similar wallets are useful analogues,
but they are not connected by real money flow.

## 4. Evidence contract

Each evidence item contains:

- a unique evidence ID;
- evidence type;
- observation time;
- temporal-validity flag;
- provenance;
- structured payload.

Path payloads include every node, edge, relation, amount, timestamp, endpoint
label, and path score. Generated claims can therefore be traced back to exact
retrieved facts.

## 5. Generation

The default generator is deterministic and fully offline. The optional
OpenAI-compatible client can call a local or hosted instruction model.

The prompt requires the model to:

- cite evidence IDs;
- preserve direction and numerical values;
- distinguish paths from vector analogues;
- avoid causal or legal conclusions;
- abstain when evidence is insufficient.

Unknown citations or citation-free outputs are rejected. The pipeline then
returns the deterministic fallback explanation.

## 6. Neo4j role

The public demonstration uses an in-memory graph for reproducibility and zero
setup. The schema in `neo4j_schema.cypher` shows how the same typed records can
be represented in Neo4j for indexed graph traversal and visual inspection.

The dissertation-scale implementation can replace the in-memory store without
changing the evidence contract or generation layer.

