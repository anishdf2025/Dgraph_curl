# Incremental Entity Processing

## Overview

The system now supports **granular entity-level tracking** instead of a single `processed_to_dgraph: true` flag. This allows you to add new entity fields to existing documents without reprocessing everything.

## How It Works

### Old System (Single Flag)
```json
{
  "title": "Asha Devi v. Delhi Police",
  "court": "Supreme Court of India",
  "court_location": "New Delhi",
  "processed_to_dgraph": true  ← Single flag for everything
}
```

**Problem**: If you add `court_bench` later, you need to reprocess the entire judgment!

### New System (Granular Tracking)
```json
{
  "title": "Asha Devi v. Delhi Police",
  "court": "Supreme Court of India",
  "court_location": "New Delhi",
  "court_bench": "Division Bench",  ← New field added
  "processed_entities": {
    "judgment": true,
    "citations": true,
    "judges": true,
    "advocates": true,
    "outcome": true,
    "case_duration": true,
    "court": true,
    "court_bench": false  ← Not processed yet!
  }
}
```

**Benefit**: Process ONLY the `court_bench` field without touching citations, judges, etc.

---

## Entity Types Tracked

The system tracks these entities individually:

1. `judgment` - Main judgment node
2. `citations` - Cited cases
3. `judges` - Judges who heard the case
4. `advocates` - Petitioner and respondent advocates
5. `outcome` - Case outcome
6. `case_duration` - Duration of case
7. `court` - Court information
8. `court_bench` - **NEW**: Bench type (Division/Single/etc.)
9. `decision_date` - Decision date
10. `filing_date` - Filing date
11. `petitioner_party` - Petitioner parties
12. `respondant_party` - Respondent parties
13. `case_number` - Case number
14. `summary` - Case summary
15. `case_type` - Type of case
16. `neutral_citation` - Neutral citation
17. `acts` - Acts cited

---

## Processing New Fields for Existing Documents

### Scenario: You Already Processed 1000 Judgments

Your old documents have:
```json
{
  "court": "Supreme Court of India",
  "court_location": "New Delhi",
  "processed_entities": {
    "court": true
  }
}
```

Now you add `court_bench` to your data source:
```json
{
  "court": "Supreme Court of India",
  "court_location": "New Delhi",
  "court_bench": "Division Bench"  ← NEW!
}
```

### Solution: Process Only the New Field

```bash
# Step 1: Update your data in Elasticsearch
curl -X POST "http://localhost:9200/graphdb/_update/doc_id" -H 'Content-Type: application/json' -d'{
  "doc": {
    "court_bench": "Division Bench"
  }
}'

# Step 2: Process ONLY court_bench for existing documents
python3 process_new_entity.py --entity court_bench

# Or dry-run first to see what would be processed
python3 process_new_entity.py --entity court_bench --dry-run
```

---

## Available Commands

### 1. Process Specific Entity
```bash
# Process only court_bench
python3 process_new_entity.py --entity court_bench

# Process only acts
python3 process_new_entity.py --entity acts
```

### 2. Dry Run (Preview)
```bash
# See what would be processed without actually processing
python3 process_new_entity.py --entity court_bench --dry-run
```

### 3. Process All New Fields
```bash
# Process all new entity fields at once
python3 process_new_entity.py --entity all
```

---

## Example Workflow: Adding `court_bench`

### Step 1: Update Schema
Add `bench_type` to Court entity in `schema.py`:
```python
type Court {
  court_id
  name
  location
  bench_type  # NEW
}

bench_type: string @index(exact, term) @upsert .  # NEW
```

### Step 2: Update Court Handler
Update `relations/court.py` to extract and process `court_bench`:
```python
def extract_court(self, source):
    court_name = source.get('court', '').strip()
    court_location = source.get('court_location', '').strip()
    court_bench = source.get('court_bench', '').strip()  # NEW
    return (court_name, court_location, court_bench)
```

### Step 3: Update Elasticsearch Documents
Add `court_bench` to your existing documents:
```bash
# Example: Update a single document
curl -X POST "http://localhost:9200/graphdb/_update/doc_id" -H 'Content-Type: application/json' -d'{
  "doc": {
    "court_bench": "Division Bench"
  }
}'

# Or bulk update with script
curl -X POST "http://localhost:9200/graphdb/_update_by_query" -H 'Content-Type: application/json' -d'{
  "script": {
    "source": "ctx._source.court_bench = params.bench",
    "params": {
      "bench": "Division Bench"
    }
  },
  "query": {
    "term": {
      "court": "Supreme Court of India"
    }
  }
}'
```

### Step 4: Process Only court_bench
```bash
# Preview what will be processed
python3 process_new_entity.py --entity court_bench --dry-run

# Process it
python3 process_new_entity.py --entity court_bench
```

### Step 5: Verify in Dgraph
```bash
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{ court(func: type(Court)) { court_id name location bench_type } }"
}'
```

---

## How Dgraph Updates Work

### Upsert Mechanism
When you process `court_bench` for existing documents:

1. **Query** finds existing Court node by `name + location`
2. **Mutation** adds `bench_type` to that existing node
3. **Result**: Court node now has the new field **without creating duplicates**

### Example Mutation
```json
{
  "query": {
    "court_c856d8650786 as var(func: eq(name, \"Supreme Court of India\")) @filter(type(Court) AND eq(location, \"New Delhi\"))"
  },
  "set": [
    {
      "uid": "uid(court_c856d8650786)",
      "court_id": "court_c856d8650786",
      "name": "Supreme Court of India",
      "location": "New Delhi",
      "bench_type": "Division Bench",  ← NEW field added
      "dgraph.type": "Court"
    }
  ]
}
```

---

## Monitoring Status

### Check Processing Status
```bash
# Get stats from API
curl http://localhost:8005/stats

# Check specific document in Elasticsearch
curl "http://localhost:9200/graphdb/_doc/doc_id"
```

### Sample Response
```json
{
  "_id": "asha_devi_case",
  "_source": {
    "title": "Asha Devi v. Delhi Police",
    "court": "Supreme Court of India",
    "court_bench": "Division Bench",
    "processed_entities": {
      "judgment": true,
      "citations": true,
      "judges": true,
      "court": true,
      "court_bench": true  ← Now processed!
    },
    "last_dgraph_update": "2025-11-12T15:55:00.000Z"
  }
}
```

---

## Benefits

### ✅ No Duplicate Processing
- Already processed entities stay marked as `true`
- Only new entities get processed

### ✅ Incremental Schema Evolution
- Add new fields anytime
- No need to reprocess 1000s of documents

### ✅ Fine-Grained Control
- Process specific entities only
- Skip what's already done

### ✅ Audit Trail
- `last_dgraph_update` timestamp
- Per-entity processing status
- Clear visibility into what's processed

---

## Troubleshooting

### Issue: All documents show as unprocessed
**Cause**: You're using the old single-flag system  
**Solution**: Documents will automatically migrate to granular tracking on next processing

### Issue: court_bench not appearing in Dgraph
**Check**:
1. Is `court_bench` in your Elasticsearch documents?
2. Is `bench_type` in your schema?
3. Does `relations/court.py` extract `court_bench`?
4. Run: `python3 process_new_entity.py --entity court_bench --dry-run`

### Issue: Script can't find documents
**Check**:
1. Elasticsearch is running: `curl localhost:9200`
2. Index exists: `curl localhost:9200/graphdb`
3. Documents have the field: `curl "localhost:9200/graphdb/_search?q=court_bench:*"`

---

## Migration from Old System

Existing documents with `processed_to_dgraph: true` will work fine. The system supports both modes:

- **Legacy mode**: `processed_to_dgraph: true` (entire document)
- **New mode**: `processed_entities: { ... }` (per entity)

New documents will automatically use the granular tracking system.
