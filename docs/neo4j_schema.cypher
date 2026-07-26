// Portfolio-safe Neo4j schema for the synthetic demonstration.
// This file defines constraints and representative query patterns only.

CREATE CONSTRAINT wallet_id_unique IF NOT EXISTS
FOR (w:Wallet) REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.id IS UNIQUE;

CREATE INDEX wallet_label IF NOT EXISTS
FOR (w:Wallet) ON (w.label);

CREATE INDEX transaction_time IF NOT EXISTS
FOR (t:Transaction) ON (t.observed_time);

// Expected relationships:
// (:Wallet)-[:INPUTS_TO {
//   edge_id: STRING,
//   observed_time: INTEGER,
//   amount: FLOAT,
//   currency: STRING
// }]->(:Transaction)
//
// (:Transaction)-[:OUTPUTS_TO {
//   edge_id: STRING,
//   observed_time: INTEGER,
//   amount: FLOAT,
//   currency: STRING
// }]->(:Wallet)

// Example: retrieve a time-valid path from a query wallet to a historically
// known high-risk wallet. The application must still enforce path budgets and
// return all traversed edge properties as evidence.
MATCH path = (source:Wallet {id: $wallet_id})-[rels*1..4]->(target:Wallet)
WHERE target.label = 'high_risk'
  AND target.label_available_time <= $query_time
  AND all(rel IN rels WHERE rel.observed_time <= $query_time)
RETURN path
LIMIT $top_k;

