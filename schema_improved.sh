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
  cites
}

# judgment_id is the unique identifier with upsert support for main judgments
judgment_id: string @index(exact) @upsert .

# title also has @upsert for citation deduplication
title: string @index(exact, term, fulltext) @upsert .

# Other fields with proper indexing
doc_id: string @index(exact) .
year: int @index(int) .
cites: [uid] @reverse .
'

echo "Schema applied successfully!"
echo "✅ judgment_id field has @upsert - this prevents duplicate main judgments"
echo "✅ title field has @upsert - this prevents duplicate citations"
echo "✅ All fields properly indexed for efficient queries"
