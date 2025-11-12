# Dgraph Monitor API

Continuous monitoring system that automatically detects new entries in Elasticsearch and pushes them to Dgraph.

## Features

✅ **Automatic Monitoring**: Continuously checks Elasticsearch for new entries every 30 seconds  
✅ **Smart Detection**: Only processes documents where `processed_to_dgraph != true`  
✅ **Automatic Marking**: Updates Elasticsearch with `processed_to_dgraph: true` after successful upload  
✅ **Duplicate Prevention**: Uses hash-based deduplication for all entities  
✅ **REST API**: Full control via HTTP endpoints  
✅ **Background Processing**: Non-blocking continuous monitoring  
✅ **Logging**: Detailed logs in `dgraph_monitor.log` file  
✅ **Error Handling**: Resilient to failures, keeps retrying

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Elasticsearch  │ ───→ │  FastAPI Monitor │ ───→ │   Dgraph    │
│   (graphdb)     │      │  (Background)    │      │  (port 8180)│
└─────────────────┘      └──────────────────┘      └─────────────┘
         ↑                        │
         │                        │
         └────────────────────────┘
           Updates processed_to_dgraph: true
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Services Running

Ensure these services are running:
- **Elasticsearch**: `http://localhost:9200`
- **Dgraph**: `http://localhost:8180`

### 3. Start the API

```bash
python3 fastapi_dgraph_monitor.py
```

Or with uvicorn:

```bash
uvicorn fastapi_dgraph_monitor:app --host 0.0.0.0 --port 8000 --reload
```

The API will start on `http://localhost:8000`

## API Endpoints

### 📊 Check Status

```bash
curl http://localhost:8000/status
```

Returns:
```json
{
  "is_running": true,
  "last_check": "2025-11-10T13:45:30.123456",
  "total_processed": 15,
  "last_batch_size": 3,
  "check_interval_seconds": 30,
  "recent_errors": []
}
```

### ▶️ Start Monitoring

```bash
curl -X POST http://localhost:8000/start
```

This will:
1. Apply Dgraph schema
2. Start background monitoring task
3. Check every 30 seconds for new documents
4. Automatically process and mark them

### ⏹️ Stop Monitoring

```bash
curl -X POST http://localhost:8000/stop
```

### ⚡ Process Now (Manual Trigger)

```bash
curl -X POST http://localhost:8000/process-now
```

Forces immediate processing of all unprocessed documents.

### 📈 Get Statistics

```bash
curl http://localhost:8000/stats
```

Returns detailed statistics:
```json
{
  "elasticsearch": {
    "total_documents": 25,
    "processed_documents": 20,
    "unprocessed_documents": 5
  },
  "monitor": {
    "is_running": true,
    "total_processed_by_monitor": 20,
    "last_check": "2025-11-10T13:45:30.123456",
    "last_batch_size": 5
  },
  "dgraph": {
    "citations_tracked": 35,
    "judges_tracked": 42,
    "advocates_tracked": 58,
    "outcomes_tracked": 2,
    "case_durations_tracked": 18
  }
}
```

### 📖 API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## Usage Workflow

### Typical Usage

1. **Start the API once**:
   ```bash
   python3 fastapi_dgraph_monitor.py
   ```

2. **Start monitoring**:
   ```bash
   curl -X POST http://localhost:8000/start
   ```

3. **Let it run**: The system will now automatically:
   - Check Elasticsearch every 30 seconds
   - Detect new documents
   - Build mutations
   - Upload to Dgraph
   - Mark as processed

4. **Add new documents to Elasticsearch**: Just add them normally. The monitor will detect and process them automatically.

5. **Check progress anytime**:
   ```bash
   curl http://localhost:8000/status
   ```

### Manual Processing

If you want to process immediately without waiting:

```bash
curl -X POST http://localhost:8000/process-now
```

## How It Works

### 1. Detection
The monitor queries Elasticsearch for documents where:
```json
{
  "query": {
    "bool": {
      "should": [
        {"bool": {"must_not": {"exists": {"field": "processed_to_dgraph"}}}},
        {"term": {"processed_to_dgraph": false}}
      ]
    }
  }
}
```

### 2. Processing
For each unprocessed document:
- Extract all fields (title, citations, judges, advocates, etc.)
- Generate unique IDs using hash-based deduplication
- Build upsert mutation with proper relationships
- Upload to Dgraph

### 3. Marking
After successful upload:
```json
{
  "processed_to_dgraph": true,
  "dgraph_processed_at": "2025-11-10T13:45:30.123456"
}
```

## Configuration

Edit these variables in `fastapi_dgraph_monitor.py`:

```python
ES_HOST = "http://localhost:9200"      # Elasticsearch host
ES_INDEX_NAME = "graphdb"              # Elasticsearch index name
DGRAPH_HOST = "http://localhost:8180"  # Dgraph host
OUTPUT_FILE = "dgraph_mutations_all.json"  # Mutation file output
CHECK_INTERVAL = 30                    # Check interval in seconds
```

## Logging

All activity is logged to:
- **File**: `dgraph_monitor.log`
- **Console**: Real-time output

Log format:
```
2025-11-10 13:45:30 - INFO - Found 3 unprocessed documents
2025-11-10 13:45:31 - INFO - Mutation built: 45 total nodes
2025-11-10 13:45:32 - INFO - Data uploaded to Dgraph successfully
2025-11-10 13:45:32 - INFO - Marked 3 documents as processed
```

## Error Handling

The system is resilient:
- **Connection Failures**: Retries automatically
- **Partial Failures**: Continues processing remaining documents
- **Schema Errors**: Logs and continues
- **API Errors**: Recent errors available via `/status` endpoint

## Testing

### 1. Add Test Document to Elasticsearch

```bash
curl -X POST "http://localhost:9200/graphdb/_doc/test_1" -H 'Content-Type: application/json' -d'
{
  "title": "Test Case v. Example Corp",
  "doc_id": "test_1",
  "year": 2025,
  "citations": ["Previous Case (2020) 1 SCC 123"],
  "judges": ["Justice Test Judge"],
  "petitioner_advocates": ["Mr. Test Advocate"],
  "respondant_advocates": ["Ms. Response Advocate"],
  "outcome": "Petitioner Won",
  "case_duration": "2025-01-01 to 2025-06-01",
  "processed_timestamp": "2025-11-10T13:00:00"
}
'
```

### 2. Check if Detected

Within 30 seconds, the monitor will detect and process it.

Check status:
```bash
curl http://localhost:8000/status
```

### 3. Verify in Elasticsearch

```bash
curl "http://localhost:9200/graphdb/_doc/test_1?pretty"
```

Should now have:
```json
{
  "processed_to_dgraph": true,
  "dgraph_processed_at": "2025-11-10T13:45:30.123456"
}
```

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/dgraph-monitor.service`:

```ini
[Unit]
Description=Dgraph Monitor API
After=network.target elasticsearch.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/anish/Desktop/Anish/Dgraph_curl
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 fastapi_dgraph_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable dgraph-monitor
sudo systemctl start dgraph-monitor
sudo systemctl status dgraph-monitor
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_dgraph_monitor.py .

EXPOSE 8000

CMD ["uvicorn", "fastapi_dgraph_monitor:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t dgraph-monitor .
docker run -d -p 8000:8000 --name dgraph-monitor dgraph-monitor
```

### Using PM2 (Node.js Process Manager)

```bash
pm2 start fastapi_dgraph_monitor.py --interpreter python3 --name dgraph-monitor
pm2 startup
pm2 save
```

## Troubleshooting

### Monitor not detecting new documents

1. Check Elasticsearch connection:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

2. Check if documents have the field set:
   ```bash
   curl "http://localhost:9200/graphdb/_search?pretty" -H 'Content-Type: application/json' -d'
   {
     "query": {
       "bool": {
         "must_not": {"exists": {"field": "processed_to_dgraph"}}
       }
     }
   }'
   ```

3. Check logs:
   ```bash
   tail -f dgraph_monitor.log
   ```

### Dgraph connection failed

1. Verify Dgraph is running:
   ```bash
   curl http://localhost:8180/health
   ```

2. Check Dgraph logs

### API not starting

1. Check if port 8000 is available:
   ```bash
   lsof -i :8000
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Performance

- **Check Interval**: 30 seconds (configurable)
- **Batch Size**: Up to 100 documents per batch
- **Memory**: Minimal (uses scroll API for large datasets)
- **CPU**: Low (async operations)

## Security Considerations

For production:

1. **Add Authentication**: Use FastAPI security features
2. **Use HTTPS**: Configure SSL/TLS
3. **Firewall**: Restrict access to port 8000
4. **Environment Variables**: Store credentials securely
5. **Rate Limiting**: Add rate limiting middleware

## License

MIT License

## Support

For issues or questions:
- Check logs: `dgraph_monitor.log`
- View stats: `curl http://localhost:8000/stats`
- Check status: `curl http://localhost:8000/status`
