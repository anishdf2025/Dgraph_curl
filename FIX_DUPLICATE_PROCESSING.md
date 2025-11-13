# Fix: Preventing Duplicate Document Processing

## Problem
The pipeline was processing and pushing the **same documents to Dgraph repeatedly** every 30 seconds, even though they had already been processed. This happened because:

1. Documents were being fetched from Elasticsearch based on `processed_to_dgraph != true`
2. When marking documents as processed, only `processed_entities` field was being updated
3. The `processed_to_dgraph` field was **not being set to true**
4. So in the next cycle, the same documents would be fetched again

## Solution
Updated the `mark_documents_processed()` function in `elasticsearch_client.py` to:

### Before:
```python
# Only updated processed_entities, but NOT processed_to_dgraph
ctx._source.last_dgraph_update = params.timestamp;
```

### After:
```python
# Now ALSO sets processed_to_dgraph = true
ctx._source.last_dgraph_update = params.timestamp;
ctx._source.processed_to_dgraph = true;
ctx._source.dgraph_processed_at = params.timestamp;
```

## What Changed

### 1. **elasticsearch_client.py** - `mark_documents_processed()`
- Added `processed_to_dgraph = true` in the script
- Added `dgraph_processed_at` timestamp
- This ensures documents are properly marked as processed

### 2. **api_endpoints.py** - `process_now()`
- Added entity_types parameter when calling `mark_documents_processed()`
- Ensures consistency with monitoring loop

## Expected Behavior Now

✅ **First Run**: 
- Fetches unprocessed documents (where `processed_to_dgraph != true`)
- Builds mutation and pushes to Dgraph
- Marks documents with `processed_to_dgraph = true`

✅ **Second Run (30 seconds later)**:
- Fetches unprocessed documents
- **Finds 0 documents** (because all were marked as processed)
- Logs: "📭 No new documents to process"
- **Does NOT create duplicate mutations or push to Dgraph**

✅ **When New Document Added**:
- New document has `processed_to_dgraph != true` (or field doesn't exist)
- Pipeline processes **ONLY the new document**
- Marks it as processed
- Next cycle finds 0 unprocessed documents again

## Testing

To verify the fix is working:

1. **Check logs for duplicate processing:**
   ```bash
   tail -f dgraph_monitor.log
   ```
   You should see:
   ```
   Found 0 unprocessed documents
   📭 No new documents to process
   ```

2. **Add a new test document:**
   ```bash
   curl -X POST "http://localhost:9200/graphdb/_doc/" -H 'Content-Type: application/json' -d'{
     "title": "Test Case v. Example",
     "court": "Test Court"
   }'
   ```

3. **Verify it gets processed once:**
   - First cycle: "Found 1 unprocessed documents"
   - Second cycle: "Found 0 unprocessed documents"

4. **Check Elasticsearch document:**
   ```bash
   curl "http://localhost:9200/graphdb/_search?q=title:Test*&pretty"
   ```
   Verify the document has:
   - `"processed_to_dgraph": true`
   - `"dgraph_processed_at": "<timestamp>"`
   - `"processed_entities": { "judgment": true, "citations": true, ... }`

## Key Points

- ✅ Documents are now marked with `processed_to_dgraph = true` after successful processing
- ✅ Only NEW documents (without this flag) will be processed
- ✅ No duplicate mutations or pushes to Dgraph
- ✅ Pipeline is now idempotent - running multiple times won't create duplicates
- ✅ Both monitoring loop and manual `process_now` endpoint use consistent marking

## Restart Required

After this fix, restart the API server:

```bash
# Stop current server (Ctrl+C)
# Then restart
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

The monitoring will automatically start and will now only process new documents!
