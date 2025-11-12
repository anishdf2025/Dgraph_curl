# 🎯 GRANULAR ENTITY TRACKING - IMPLEMENTATION SUMMARY

## What Changed?

### ✅ **NEW FEATURE**: Individual Entity Tracking

**Before:**
- Single `processed_to_dgraph: true` flag
- All-or-nothing processing
- Adding new fields = reprocess everything 😢

**After:**
- Granular `processed_entities` object
- Per-entity tracking
- Adding new fields = process only that entity 🎉

---

## Files Modified

### 1. `elasticsearch_client.py`
**Changes:**
- `fetch_unprocessed_documents()` - Now accepts `entity_type` parameter
- `mark_documents_processed()` - Now accepts `entity_types` list
- Uses scripted updates to merge entity tracking

### 2. `monitor.py`
**Changes:**
- Defines all 17 entity types
- Passes entity_types list when marking documents processed

### 3. `process_new_entity.py` (NEW FILE)
**Purpose:**
- Process specific entities for existing documents
- Supports: `court_bench`, `acts`, `all`
- Has `--dry-run` mode to preview

### 4. `INCREMENTAL_PROCESSING.md` (NEW FILE)
**Purpose:**
- Complete documentation
- Usage examples
- Troubleshooting guide

---

## How Your Data Looks Now

### Elasticsearch Document Structure

```json
{
  "_id": "asha_devi_case",
  "_source": {
    "title": "Asha Devi v. Delhi Police",
    "court": "Supreme Court of India",
    "court_location": "New Delhi",
    "court_bench": "Division Bench",
    
    "processed_entities": {
      "judgment": true,
      "citations": true,
      "judges": true,
      "advocates": true,
      "outcome": true,
      "case_duration": true,
      "court": true,
      "court_bench": false,  ← Ready to process!
      "decision_date": false,
      "filing_date": false,
      "petitioner_party": false,
      "respondant_party": false,
      "case_number": false,
      "summary": false,
      "case_type": false,
      "neutral_citation": false,
      "acts": false
    },
    
    "last_dgraph_update": "2025-11-12T16:00:00.000Z"
  }
}
```

---

## Usage Examples

### ✅ Example 1: Process Only court_bench

```bash
# Step 1: Check what would be processed
python3 process_new_entity.py --entity court_bench --dry-run

# Output:
# Found 1 documents with unprocessed 'court_bench' field
# DRY RUN: Would process 1 documents
#   - xeTFbJoBE4wsznJVFsGb: Asha Devi v. Delhi Police

# Step 2: Actually process it
python3 process_new_entity.py --entity court_bench

# Result: Only Court entity updated with bench_type
# Citations, Judges, etc. are NOT touched!
```

### ✅ Example 2: Add New Acts Field Later

```bash
# Your new data comes with 'acts' field
curl -X POST "http://localhost:9200/graphdb/_update/doc_id" -H 'Content-Type: application/json' -d'{
  "doc": {
    "acts": ["Information Technology Act, 2000", "IPC Section 420"]
  }
}'

# Process only acts for documents that have it
python3 process_new_entity.py --entity acts

# Result: Only Act entities created
# Everything else untouched!
```

### ✅ Example 3: Normal Monitoring (All Entities)

```bash
# Start normal monitoring - processes ALL entities for new documents
uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# This will:
# 1. Find documents where processed_to_dgraph != true
# 2. Process all 17 entity types
# 3. Mark each entity as processed individually
```

---

## Entity Types Tracked

| # | Entity Type | Source Field | Dgraph Type |
|---|-------------|--------------|-------------|
| 1 | `judgment` | `title`, `doc_id` | Judgment |
| 2 | `citations` | `citations[]` | Judgment (cited) |
| 3 | `judges` | `judges[]` | Judge |
| 4 | `advocates` | `petitioner_advocates[]`, `respondant_advocates[]` | Advocate |
| 5 | `outcome` | `outcome` | Outcome |
| 6 | `case_duration` | `case_duration` | CaseDuration |
| 7 | `court` | `court`, `court_location` | Court |
| 8 | **`court_bench`** | **`court_bench`** | **Court.bench_type** |
| 9 | `decision_date` | `decision_date` | DecisionDate |
| 10 | `filing_date` | `filing_date` | FilingDate |
| 11 | `petitioner_party` | `petitioner_party` | PetitionerParty |
| 12 | `respondant_party` | `respondant_party` | RespondantParty |
| 13 | `case_number` | `case_number` | CaseNumber |
| 14 | `summary` | `summary` | Summary |
| 15 | `case_type` | `case_type` | CaseType |
| 16 | `neutral_citation` | `neutral_citation` | NeutralCitation |
| 17 | **`acts`** | **`acts[]`** | **Act** |

---

## Next Steps

### To Add court_bench Field Support:

#### 1. Update Schema (`schema.py`)
```python
type Court {
  court_id
  name
  location
  bench_type  # ADD THIS
}

bench_type: string @index(exact, term) @upsert .  # ADD THIS
```

#### 2. Update Court Handler (`relations/court.py`)
```python
def extract_court(self, source):
    court_bench = source.get('court_bench', '').strip()  # ADD THIS
    return (court_name, court_location, court_bench)  # ADD court_bench

def build_query_parts(self, court_name, court_location, court_bench=None):  # ADD parameter
    # Store bench_type in local_courts dict
    self.local_courts[court_key] = {
        'hash': court_hash,
        'name': court_name,
        'location': court_location,
        'bench_type': court_bench  # ADD THIS
    }

def build_court_nodes(self):
    if court_data.get('bench_type'):  # ADD THIS
        court_node["bench_type"] = court_data['bench_type']
```

#### 3. Update Mutation Builder (`mutation_builder.py`)
```python
# Line 100: Update to unpack 3 values
court_name, court_location, court_bench = self.court_handler.extract_court(source)
court_queries, court_var = self.court_handler.build_query_parts(court_name, court_location, court_bench)
```

#### 4. Apply Schema and Process
```bash
# Apply schema
curl -X POST localhost:8180/admin/schema --data-binary '@schema.py'

# Process court_bench for existing documents
python3 process_new_entity.py --entity court_bench

# Start monitoring for new documents
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

---

## Testing Your Current Data

```bash
# 1. Check what's ready to process
python3 process_new_entity.py --entity court_bench --dry-run

# Expected Output:
# Found 1 documents with unprocessed 'court_bench' field
#   - xeTFbJoBE4wsznJVFsGb: Asha Devi v. Delhi Police

# 2. Check document in Elasticsearch
curl "http://localhost:9200/graphdb/_doc/xeTFbJoBE4wsznJVFsGb?pretty"

# 3. Check if Court exists in Dgraph
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{ courts(func: type(Court)) { uid court_id name location bench_type } }"
}'
```

---

## Benefits of This Approach

### 🎯 **Incremental Schema Evolution**
- Add `court_bench` today
- Add `acts` next month
- Add `court_division` next year
- Never reprocess old entities!

### 💾 **Storage Efficient**
- Only process what's new
- No duplicate processing
- Clear audit trail

### 🚀 **Performance**
- Targeted updates
- No wasted computation
- Fast incremental processing

### 📊 **Visibility**
- Know exactly what's processed
- Per-entity status
- Easy debugging

---

## Quick Reference Commands

```bash
# Preview what would be processed
python3 process_new_entity.py --entity court_bench --dry-run

# Process specific entity
python3 process_new_entity.py --entity court_bench

# Process all new entities
python3 process_new_entity.py --entity all

# Start normal monitoring (processes everything)
uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# Check document status
curl "http://localhost:9200/graphdb/_doc/DOC_ID?pretty"

# Query Dgraph for Courts with bench_type
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{ q(func: has(bench_type)) { uid name location bench_type } }"
}'
```

---

## Ready to Use! 🎉

The system is now configured for **granular entity tracking**. You can:

1. ✅ Add new fields anytime
2. ✅ Process only what's new
3. ✅ Never reprocess old data
4. ✅ Have full visibility into what's processed

**Your next command:**
```bash
python3 process_new_entity.py --entity court_bench --dry-run
```

This will show you exactly what would happen without actually processing anything!
