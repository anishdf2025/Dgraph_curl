#!/bin/bash
echo 'Uploading mutations to Dgraph...'
echo "Uploading mutation_0001.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0001.json
echo ""
echo "Uploading mutation_0002.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0002.json
echo ""
echo "Uploading mutation_0003.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0003.json
echo ""
echo "Uploading mutation_0004.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0004.json
echo ""
echo "Uploading mutation_0005.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0005.json
echo ""
echo "Uploading mutation_0006.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0006.json
echo ""
echo "Uploading mutation_0007.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0007.json
echo ""
echo "Uploading mutation_0008.json..."
curl -X POST "localhost:8180/mutate?commitNow=true" \
     -H "Content-Type: application/json" \
     --data-binary @upsert_mutations_no_citation_duplicates/mutation_0008.json
echo ""
echo "All mutations uploaded!"
