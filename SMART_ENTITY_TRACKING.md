# Smart Entity Tracking - Only Mark Entities That Exist

## Problem
Previously, the system was marking **ALL entity types as `true`** for every document, even if those entities didn't exist in the document:

```json
{
  "processed_entities": {
    "judgment": true,
    "citations": true,      ❌ Document may not have citations
    "judges": true,         ❌ Document may not have judges  
    "advocates": true,      ❌ Document may not have advocates
    "outcome": true,        ❌ Document may not have outcome
    "case_duration": true,  ❌ Document may not have duration
    "court": true,          ❌ Document may not have court
    "decision_date": true,  ❌ Document may not have this
    "filing_date": true,    ❌ Document may not have this
    // ... and so on for 16 entity types
  }
}
```

This was **incorrect** because:
- A document with only `title` and `court` would be marked as having all 16 entities
- Makes tracking inaccurate
- Can't identify which specific entities need updating

## Solution
Created **smart entity detection** that:
1. ✅ Scans each document to detect which entities **actually exist**
2. ✅ Only marks those specific entities as `processed = true`
3. ✅ Each document has its own custom entity list

## New Files

### 1. `entity_detector.py`
New module that detects which entities are present in each document:

```python
def detect_entities_in_document(doc: Dict) -> List[str]:
    """Detect which entities are present in a document"""
    # Returns only entities that exist
    # Example: ["judgment", "court", "outcome"]
```

**Example Detection:**
```python
# Document 1: Has title, court, judges
entities = ["judgment", "court", "judges"]

# Document 2: Has title, citations, outcome
entities = ["judgment", "citations", "outcome"]

# Document 3: Has only title
entities = ["judgment"]
```

## Changes Made

### 1. **elasticsearch_client.py**
Added new function `mark_documents_with_per_doc_entities()`:

```python
def mark_documents_with_per_doc_entities(es, doc_entities):
    """
    Mark each document with ONLY the entities it contains
    
    Args:
        doc_entities: {"doc_id_1": ["judgment", "court"], 
                      "doc_id_2": ["judgment", "citations", "judges"]}
    """
```

### 2. **monitor.py**
Updated to use entity detection:

**Before:**
```python
# Hardcoded list of ALL entities
entity_types = ['judgment', 'citations', 'judges', ...all 16 entities]
mark_documents_processed(es, documents, entity_types)
```

**After:**
```python
# Detect which entities exist in each document
doc_entities = detect_entities_in_batch(documents)
# Returns: {"doc1": ["judgment", "court"], "doc2": ["judgment", "judges"]}

mark_documents_with_per_doc_entities(es, doc_entities)
```

### 3. **api_endpoints.py**
Same update for the `/process-now` endpoint

## Detection Logic

The `entity_detector.py` checks for each entity:

| Entity Type | Check Logic |
|-------------|-------------|
| `judgment` | Always included if `title` exists |
| `citations` | Checks if `citations` array exists and has length > 0 |
| `judges` | Checks if `judges` array exists and has length > 0 |
| `advocates` | Checks if `petitioner_advocates` OR `respondant_advocates` exist |
| `outcome` | Checks if `outcome` field exists and not empty |
| `case_duration` | Checks if `case_duration` field exists |
| `court` | Checks if `court` field exists |
| `decision_date` | Checks if `decision_date` field exists |
| `filing_date` | Checks if `filing_date` field exists |
| `petitioner_party` | Checks if `petitioner_party` field exists |
| `respondant_party` | Checks if `respondant_party` field exists |
| `case_number` | Checks if `case_number` field exists |
| `summary` | Checks if `summary` field exists |
| `case_type` | Checks if `case_type` field exists |
| `neutral_citation` | Checks if `neutral_citation` field exists |
| `acts` | Checks if `acts` array exists and has length > 0 |

## Example Scenarios

### Scenario 1: Full Document
```json
{
  "title": "Case A v. Case B",
  "court": "Supreme Court",
  "judges": ["Justice A"],
  "outcome": "Petitioner Won",
  "citations": ["Case X", "Case Y"]
}
```

**Marked Entities:**
```json
{
  "processed_entities": {
    "judgment": true,
    "court": true,
    "judges": true,
    "outcome": true,
    "citations": true
  }
}
```
✅ **Only 5 entities marked** (not all 16)

### Scenario 2: Minimal Document
```json
{
  "title": "Case C v. Case D",
  "court": "High Court"
}
```

**Marked Entities:**
```json
{
  "processed_entities": {
    "judgment": true,
    "court": true
  }
}
```
✅ **Only 2 entities marked**

### Scenario 3: Complex Document
```json
{
  "title": "Case E v. Case F",
  "court": "District Court",
  "court_location": "Mumbai",
  "court_bench": "Division Bench",
  "judges": ["Justice X", "Justice Y"],
  "petitioner_advocates": ["Adv. A"],
  "respondant_advocates": ["Adv. B"],
  "outcome": "Dismissed",
  "case_duration": "2020-01-01 to 2021-06-30",
  "citations": ["Ref 1", "Ref 2", "Ref 3"],
  "decision_date": "2021-06-30",
  "case_number": "CRL.A. 123/2020"
}
```

**Marked Entities:**
```json
{
  "processed_entities": {
    "judgment": true,
    "court": true,
    "judges": true,
    "advocates": true,
    "outcome": true,
    "case_duration": true,
    "citations": true,
    "decision_date": true,
    "case_number": true
  }
}
```
✅ **Only 9 entities marked** (only those that exist)

## Benefits

1. **✅ Accurate Tracking**
   - Know exactly which entities each document has
   - Can query: "Which documents don't have citations?"

2. **✅ Selective Updates**
   - Update only specific entities without reprocessing all
   - Example: Add `acts` field later without affecting other entities

3. **✅ Better Debugging**
   - Clear visibility of what was processed
   - Easy to identify incomplete documents

4. **✅ Efficient Processing**
   - Don't waste resources marking non-existent entities
   - Smaller update payloads to Elasticsearch

5. **✅ Future-Proof**
   - Add new entity types without breaking existing data
   - Can incrementally add new fields

## Testing

### Test Case 1: Verify Smart Detection
```bash
# Add a document with only title and court
curl -X POST "http://localhost:9200/graphdb/_doc/test_1" -H 'Content-Type: application/json' -d'{
  "title": "Test Case",
  "court": "Test Court"
}'

# Wait for processing (30 seconds)

# Check the document
curl "http://localhost:9200/graphdb/_doc/test_1?pretty"

# Should show:
# "processed_entities": {
#   "judgment": true,
#   "court": true
# }
# NOT all 16 entities!
```

### Test Case 2: Verify Full Document
```bash
# Add a document with many entities
curl -X POST "http://localhost:9200/graphdb/_doc/test_2" -H 'Content-Type: application/json' -d'{
  "title": "Full Test Case",
  "court": "Supreme Court",
  "judges": ["Judge A"],
  "outcome": "Won",
  "citations": ["Ref 1"]
}'

# Check processed_entities - should have 5 entities only
```

## Migration

**No migration needed!** The existing `processed_to_dgraph` flag is still set to `true`, so:
- ✅ Already processed documents won't be reprocessed
- ✅ New documents get smart entity tracking
- ✅ Backward compatible

## Restart to Apply

```bash
# Stop the server (Ctrl+C)
# Then restart
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

Now the system will **only mark entities that actually exist** in each document! 🎯
