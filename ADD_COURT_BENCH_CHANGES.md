# Adding court_bench Field - Exact Code Changes

## Overview
This document shows the **exact code changes** needed to add `court_bench` support to your system.

---

## File 1: `schema.py`

### Location: Lines 53-57
**CURRENT:**
```python
type Court {
  court_id
  name
  location
}
```

**CHANGE TO:**
```python
type Court {
  court_id
  name
  location
  bench_type
}
```

### Location: Lines 142-144
**CURRENT:**
```python
# Court fields
court_id: string @index(exact) @upsert .
location: string @index(term) .
```

**CHANGE TO:**
```python
# Court fields
court_id: string @index(exact) @upsert .
location: string @index(term) .
bench_type: string @index(exact, term) @upsert .
```

---

## File 2: `relations/court.py`

### Change 1: Update extract_court method (Lines 38-51)

**CURRENT:**
```python
def extract_court(self, source: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract court information from Elasticsearch document
    
    Args:
        source: Elasticsearch document _source
        
    Returns:
        Tuple of (court_name, court_location)
    """
    court_name = source.get('court', '').strip()
    court_location = source.get('court_location', '').strip()
    
    if court_name:
        logger.debug(f"Extracted court: {court_name}" + (f" ({court_location})" if court_location else ""))
    
    return (court_name if court_name else None, court_location if court_location else None)
```

**CHANGE TO:**
```python
def extract_court(self, source: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract court information from Elasticsearch document
    
    Args:
        source: Elasticsearch document _source
        
    Returns:
        Tuple of (court_name, court_location, court_bench)
    """
    court_name = source.get('court', '').strip()
    court_location = source.get('court_location', '').strip()
    court_bench = source.get('court_bench', '').strip()
    
    if court_name:
        logger.debug(f"Extracted court: {court_name}" + 
                    (f" ({court_location})" if court_location else "") +
                    (f" - {court_bench}" if court_bench else ""))
    
    return (court_name if court_name else None, 
            court_location if court_location else None,
            court_bench if court_bench else None)
```

### Change 2: Update build_query_parts signature (Line 53)

**CURRENT:**
```python
def build_query_parts(self, court_name: str, court_location: Optional[str]) -> Tuple[List[str], Optional[str]]:
```

**CHANGE TO:**
```python
def build_query_parts(self, court_name: str, court_location: Optional[str], court_bench: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
```

### Change 3: Store bench_type in local_courts (Lines 71-77)

**CURRENT:**
```python
if court_key not in self.local_courts:
    court_hash = self.get_hash(court_key)
    self.local_courts[court_key] = {
        'hash': court_hash,
        'name': court_name,
        'location': court_location
    }
```

**CHANGE TO:**
```python
if court_key not in self.local_courts:
    court_hash = self.get_hash(court_key)
    self.local_courts[court_key] = {
        'hash': court_hash,
        'name': court_name,
        'location': court_location,
        'bench_type': court_bench
    }
```

### Change 4: Add bench_type to court nodes (Lines 106-115)

**CURRENT:**
```python
court_node = {
    "uid": f"uid(court_{court_hash})",
    "court_id": f"court_{court_hash}",
    "name": court_data['name'],
    "dgraph.type": "Court"
}
if court_data['location']:
    court_node["location"] = court_data['location']
nodes.append(court_node)
```

**CHANGE TO:**
```python
court_node = {
    "uid": f"uid(court_{court_hash})",
    "court_id": f"court_{court_hash}",
    "name": court_data['name'],
    "dgraph.type": "Court"
}
if court_data['location']:
    court_node["location"] = court_data['location']
if court_data.get('bench_type'):
    court_node["bench_type"] = court_data['bench_type']
nodes.append(court_node)
```

---

## File 3: `mutation_builder.py`

### Change: Update Court processing (Lines 100-102)

**CURRENT:**
```python
# 7. Process Court (Judgment -> Court)
court_name, court_location = self.court_handler.extract_court(source)
court_queries, court_var = self.court_handler.build_query_parts(court_name, court_location)
all_query_parts.extend(court_queries)
```

**CHANGE TO:**
```python
# 7. Process Court (Judgment -> Court)
court_name, court_location, court_bench = self.court_handler.extract_court(source)
court_queries, court_var = self.court_handler.build_query_parts(court_name, court_location, court_bench)
all_query_parts.extend(court_queries)
```

---

## Apply Changes

### Step 1: Apply Schema
```bash
curl -X POST localhost:8180/admin/schema --data-binary '@schema.py'
```

### Step 2: Test with Existing Document
```bash
# Process court_bench for documents that already have it
python3 process_new_entity.py --entity court_bench --dry-run

# If looks good, actually process it
python3 process_new_entity.py --entity court_bench
```

### Step 3: Start Server for New Documents
```bash
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

---

## Verify Changes

### Check Dgraph
```bash
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{ courts(func: type(Court)) { uid court_id name location bench_type } }"
}'
```

### Expected Result
```json
{
  "data": {
    "courts": [
      {
        "uid": "0x...",
        "court_id": "court_c856d8650786",
        "name": "Supreme Court of India",
        "location": "New Delhi",
        "bench_type": "Division Bench"
      }
    ]
  }
}
```

---

## Summary of Changes

- ✅ **3 files modified**
- ✅ **8 specific locations changed**
- ✅ **Backward compatible** (works with old data without bench_type)
- ✅ **Incremental processing** (only updates court_bench for existing docs)

All changes preserve existing functionality while adding the new `court_bench` field support!
