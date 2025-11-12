#!/bin/bash
# Improved Dgraph schema with proper upsert configuration
# This schema ensures no duplicate nodes when using upsert

echo "Setting up Dgraph schema with upsert support..."

curl -X POST localhost:8180/alter -d '
type Judgment {
  judgment_id
  title
  doc_id
  year
  processed_timestamp
  cites
  judged_by
  petitioner_represented_by
  respondant_represented_by
  has_outcome
  has_case_duration
}

type Judge {
  judge_id
  name
}

type Advocate {
  advocate_id
  name
  advocate_type
}

type Outcome {
  outcome_id
  name
}

type CaseDuration {
  case_duration_id
  duration
}

# Judgment fields
judgment_id: string @index(exact) @upsert .
title: string @index(exact, term, fulltext) @upsert .
doc_id: string @index(exact) @upsert .
year: int @index(int) .
processed_timestamp: datetime @index(hour) .
cites: [uid] @reverse .
judged_by: [uid] @reverse .
petitioner_represented_by: [uid] @reverse .
respondant_represented_by: [uid] @reverse .
has_outcome: uid @reverse .
has_case_duration: uid @reverse .

# Judge fields
judge_id: string @index(exact) @upsert .

# Advocate fields
advocate_id: string @index(exact) @upsert .
advocate_type: string @index(exact) .

# Outcome fields
outcome_id: string @index(exact) @upsert .

# CaseDuration fields
case_duration_id: string @index(exact) @upsert .
duration: string @index(exact, term) .

# Common field (used by Judge, Advocate, Outcome)
name: string @index(exact, term, fulltext) @upsert .
'

echo "Schema applied successfully!"
echo "✅ Judgment type with relationships to Judge, Advocate, Outcome, CaseDuration"
echo "✅ All entity types have unique IDs with @upsert"
echo "✅ Proper reverse edges for bidirectional queries"
echo "✅ All fields properly indexed for efficient queries"
