# Update Specific Field - Quick Guide

## Purpose
Update **ONLY** new fields in existing Dgraph entities without reprocessing everything.

## When to Use
When you add a **new field** to an existing entity type (like adding `bench_type` to Court).

---

## ✅ Example: Adding `court_bench` to Court Entity

### Step 1: Update Schema
Add the new field to `schema.py`:

```python
type Court {
  court_id
  name
  location
  bench_type  # ← NEW FIELD
}

# Add field definition
bench_type: string @index(exact, term) @upsert .
```

### Step 2: Apply Schema
```bash
curl -X POST localhost:8180/admin/schema --data-binary '@schema.py'
```

### Step 3: Check What Would Be Updated
```bash
python3 update_specific_field.py --field court_bench --dry-run
```

**Output:**
```
Found 2 documents with unprocessed 'court_bench' field
📍 Courts that would be updated:
  Court: Supreme Court of India (New Delhi)
  New bench_type: Division Bench
  Affects 2 judgment(s):
    - Asha Devi v. Delhi Police
    - Shahid Ali v. The State of Uttar Pradesh
```

### Step 4: Update the Field
```bash
python3 update_specific_field.py --field court_bench
```

**What Happens:**
1. ✅ Finds existing Court node (Supreme Court of India, New Delhi)
2. ✅ Adds `bench_type: "Division Bench"` to that Court
3. ✅ Ensures Court has all required fields (court_id, name, location, dgraph.type)
4. ✅ Connects Judgment → Court (if not already connected)
5. ✅ Marks documents as processed for `court_bench`

**What Doesn't Happen:**
- ❌ No reprocessing of citations
- ❌ No reprocessing of judges
- ❌ No reprocessing of advocates
- ❌ No duplicate Court nodes created

---

## 📊 Verify Results

### Check Court Node
```bash
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{ courts(func: type(Court)) { uid court_id name location bench_type } }"
}'
```

**Expected:**
```json
{
  "courts": [{
    "uid": "0x...",
    "court_id": "court_c856d8650786",
    "name": "Supreme Court of India",
    "location": "New Delhi",
    "bench_type": "Division Bench"  ← ✅
  }]
}
```

### Check Judgment Connection
```bash
curl -X POST "http://localhost:8180/query" -H "Content-Type: application/json" -d '{
  "query": "{
    judgment(func: eq(title, \"Shahid Ali v. The State of Uttar Pradesh\")) {
      uid title
      court_heard_in {
        uid name location bench_type
      }
    }
  }"
}'
```

---

## 🔄 Adding Future Fields

To add more fields to existing entities:

### 1. Update the script to support the new field
Edit `update_specific_field.py` and add a new function like `build_court_bench_update()`.

### 2. Add it to the choices
```python
parser.add_argument(
    '--field',
    choices=['court_bench', 'your_new_field'],  # Add here
)
```

### 3. Add the logic
```python
elif args.field == 'your_new_field':
    documents = fetch_documents_with_field(es, 'your_new_field')
    mutation = build_your_field_update(documents)
    # ... rest of logic
```

---

## 📝 Generated Files

- **`dgraph_field_update.json`** - The mutation that was applied to Dgraph
  - Useful for debugging
  - Shows exactly what was updated

---

## ⚠️ Important Notes

1. **Always run `--dry-run` first** to preview changes
2. **Apply schema before running** the update
3. **The script ensures complete nodes** - it adds all required fields (name, location, dgraph.type) even if only updating bench_type
4. **Idempotent** - Can run multiple times safely
5. **Tracks progress** - Uses `processed_entities.court_bench` flag in Elasticsearch

---

## 🎯 Summary

This script is your **minimal update tool** for adding new fields to existing entities. It:
- ✅ Only updates what's needed
- ✅ Doesn't recreate existing data
- ✅ Creates proper connections
- ✅ Marks progress granularly

Perfect for **incremental schema evolution**! 🚀
