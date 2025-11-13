# 🔄 Complete Pipeline Guide - Elasticsearch to Dgraph ETL

## 📋 Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Startup Flow](#startup-flow)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Schema Application Flow](#schema-application-flow)
6. [Data Processing Pipeline](#data-processing-pipeline)
7. [File Interaction Details](#file-interaction-details)
8. [Complete Flow Diagram](#complete-flow-diagram)

---

## Overview

This system is an **automated ETL pipeline** that continuously monitors **Elasticsearch** for new legal judgment documents and pushes them to **Dgraph** as a graph database with proper entity relationships.

### Key Components:
- **Elasticsearch**: Source database (Port: 9200)
- **Dgraph**: Target graph database (Port: 8180)
- **FastAPI**: REST API for control and monitoring (Port: 8005)
- **Background Monitor**: Continuous processing task

---

## Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    STARTUP SEQUENCE                            │
│                                                                │
│  1. FastAPI Server Starts (main.py)                           │
│     └─> Logging Setup                                         │
│     └─> Register API Routes                                   │
│     └─> Run startup_event()                                   │
│         └─> Apply Schema to Dgraph (schema.py)                │
│         └─> Start Background Monitor Task                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                  CONTINUOUS MONITORING                          │
│                    (Every 30 seconds)                          │
│                                                                │
│  monitor.py → monitor_and_process()                           │
│     │                                                          │
│     ├─> Connect to Elasticsearch                              │
│     │   (elasticsearch_client.py)                             │
│     │                                                          │
│     ├─> Fetch Unprocessed Documents                           │
│     │   Query: processed_to_dgraph != true                    │
│     │                                                          │
│     ├─> Build Mutation                                        │
│     │   (mutation_builder.py)                                 │
│     │   └─> Use relation handlers (relations/*.py)            │
│     │                                                          │
│     ├─> Upload to Dgraph                                      │
│     │   (dgraph_client.py)                                    │
│     │                                                          │
│     └─> Mark as Processed in Elasticsearch                    │
│         (elasticsearch_client.py)                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Startup Flow

### Step 1: Server Initialization

**File**: [`main.py`](main.py) (Lines 1-75)

```
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

**What Happens**:

1. **Logging Setup** (Lines 17-24)
   ```python
   logging.basicConfig(
       level=INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[FileHandler('dgraph_monitor.log'), StreamHandler()]
   )
   ```
   - Logs go to both `dgraph_monitor.log` and console

2. **FastAPI App Creation** (Lines 26-31)
   ```python
   app = FastAPI(
       title="Dgraph Monitor API",
       description="Monitors Elasticsearch and pushes to Dgraph",
       version="1.0.0"
   )
   ```

3. **Route Registration** (Lines 33-40)
   - `/` - Root/Welcome
   - `/status` - Monitor status
   - `/start` - Start monitoring
   - `/stop` - Stop monitoring
   - `/process-now` - Manual trigger
   - `/stats` - Statistics

4. **Startup Event** (Lines 43-58)
   - Prints system information
   - **Applies Dgraph Schema** (First time!)
   - **Starts Background Monitor Task**

---

### Step 2: Schema Application (Auto on Startup)

**File**: [`dgraph_client.py`](dgraph_client.py) (Lines 17-50)

**Triggered By**: `startup_event()` in [`main.py`](main.py)

**Flow**:

```
startup_event() 
    ↓
apply_dgraph_schema() [dgraph_client.py]
    ↓
Read schema from schema.py
    ↓
POST http://localhost:8180/alter
    ↓
Dgraph receives and applies schema
```

**Schema File**: [`schema.py`](schema.py)

**What Gets Pushed**:
```graphql
type Judgment {
  judgment_id
  title
  doc_id
  year
  cites              # → Judgment nodes
  judged_by          # → Judge nodes
  court_heard_in     # → Court nodes
  ...
}

type Court {
  court_id
  name
  location
  bench_type         # ← NEW field added!
}

# Predicates (fields)
title: string @index(exact, term, fulltext) @upsert .
bench_type: string @index(exact, term) @upsert .
...
```

**Endpoint Used**: `POST http://localhost:8180/alter`

**Request**:
```http
POST http://localhost:8180/alter
Content-Type: text/plain

<DGRAPH_SCHEMA from schema.py>
```

**Response**:
```json
{
  "data": {
    "code": "Success",
    "message": "Done"
  }
}
```

---

### Step 3: Background Monitor Starts

**File**: [`monitor.py`](monitor.py) (Lines 1-150)

**Triggered By**: `asyncio.create_task(monitor_and_process())` in [`main.py`](main.py) startup_event

**Loop**: Runs every 30 seconds (configurable in [`config.py`](config.py))

---

## API Endpoints Reference

### 🏠 **GET /** - Root/Welcome

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 20-32)

**Request**:
```bash
curl http://localhost:8005/
```

**Response**:
```json
{
  "message": "Dgraph Monitor API",
  "version": "1.0.0",
  "endpoints": {
    "/status": "Get current monitoring status",
    "/start": "Start continuous monitoring",
    "/stop": "Stop monitoring",
    "/process-now": "Process immediately",
    "/stats": "Get statistics"
  }
}
```

**What It Does**: Shows API information and available endpoints

---

### 📊 **GET /status** - Monitor Status

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 35-45)

**Request**:
```bash
curl http://localhost:8005/status
```

**Response**:
```json
{
  "is_running": true,
  "last_check": "2025-11-12T14:30:00",
  "total_processed": 15,
  "last_batch_size": 3,
  "check_interval_seconds": 30,
  "recent_errors": []
}
```

**What It Does**: 
- Shows if monitor is running
- Last check timestamp
- Total documents processed
- Recent errors (if any)

**Files Interacted**:
- Reads from: `models.py` (monitor_state dictionary)

---

### ▶️ **POST /start** - Start Monitoring

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 48-78)

**Request**:
```bash
curl -X POST http://localhost:8005/start
```

**Response**:
```json
{
  "message": "Monitoring started successfully",
  "check_interval_seconds": 30
}
```

**What It Does**:
1. ✅ Applies Dgraph Schema (`dgraph_client.py`)
2. ✅ Starts background monitoring task (`monitor.py`)
3. ✅ Sets `monitor_state["is_running"] = True`

**Files Interacted**:
- Calls: `dgraph_client.apply_dgraph_schema()`
- Calls: `monitor.monitor_and_process()`
- Updates: `models.monitor_state`

**Schema Application**: ✅ YES (via `apply_dgraph_schema()`)

**Note**: Normally auto-starts on server startup, so you rarely need this endpoint.

---

### ⏹️ **POST /stop** - Stop Monitoring

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 81-94)

**Request**:
```bash
curl -X POST http://localhost:8005/stop
```

**Response**:
```json
{
  "message": "Monitoring stopped successfully",
  "total_processed": 15
}
```

**What It Does**:
- Sets `monitor_state["is_running"] = False`
- Background task will stop after current cycle

**Files Interacted**:
- Updates: `models.monitor_state`

---

### ⚡ **POST /process-now** - Manual Processing

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 97-133)

**Request**:
```bash
curl -X POST http://localhost:8005/process-now
```

**Response**:
```json
{
  "message": "Processing completed successfully",
  "processed_count": 5,
  "total_nodes": 42
}
```

**What It Does**:
1. ✅ Connects to Elasticsearch
2. ✅ Fetches unprocessed documents
3. ✅ **Applies Dgraph Schema**
4. ✅ Builds mutation
5. ✅ Uploads to Dgraph
6. ✅ Marks documents as processed

**Complete Flow**:
```
POST /process-now
    ↓
connect_to_elasticsearch() [elasticsearch_client.py]
    ↓
fetch_unprocessed_documents() [elasticsearch_client.py]
    │ Query: { "term": { "processed_to_dgraph": false } }
    │ Endpoint: POST http://localhost:9200/graphdb/_search
    ↓
apply_dgraph_schema() [dgraph_client.py]
    │ Endpoint: POST http://localhost:8180/alter
    ↓
build_dgraph_mutation() [mutation_builder.py]
    │ Uses: relations/*.py (7 relation handlers)
    ↓
upload_to_dgraph() [dgraph_client.py]
    │ Saves to: dgraph_mutation_latest.json
    │ Endpoint: POST http://localhost:8180/mutate?commitNow=true
    ↓
mark_documents_processed() [elasticsearch_client.py]
    │ Update: { "doc": { "processed_to_dgraph": true } }
    │ Endpoint: POST http://localhost:9200/graphdb/_update/{doc_id}
```

**Files Interacted**:
- [`elasticsearch_client.py`](elasticsearch_client.py): `connect_to_elasticsearch()`, `fetch_unprocessed_documents()`, `mark_documents_processed()`
- [`dgraph_client.py`](dgraph_client.py): `apply_dgraph_schema()`, `upload_to_dgraph()`
- [`mutation_builder.py`](mutation_builder.py): `build_dgraph_mutation()`
- All files in `relations/` folder

**Schema Application**: ✅ YES (before building mutation)

---

### 📈 **GET /stats** - Statistics

**File**: [`api_endpoints.py`](api_endpoints.py) (Lines 136-164)

**Request**:
```bash
curl http://localhost:8005/stats
```

**Response**:
```json
{
  "elasticsearch": {
    "total_documents": 100,
    "processed_documents": 85,
    "unprocessed_documents": 15
  },
  "monitor": {
    "is_running": true,
    "total_processed_by_monitor": 85,
    "last_check": "2025-11-12T14:30:00",
    "last_batch_size": 5
  },
  "dgraph": {
    "citations_tracked": 150,
    "judges_tracked": 45,
    "advocates_tracked": 78,
    "outcomes_tracked": 2,
    "case_durations_tracked": 30,
    "courts_tracked": 12
  }
}
```

**What It Does**:
- Queries Elasticsearch for counts
- Shows monitor statistics
- Shows Dgraph entity counts

**Files Interacted**:
- [`elasticsearch_client.py`](elasticsearch_client.py): `get_elasticsearch_stats()`
- [`models.py`](models.py): `monitor_state`, `global_*` dictionaries

**Elasticsearch Queries Used**:
```bash
# Total count
POST http://localhost:9200/graphdb/_count

# Processed count
POST http://localhost:9200/graphdb/_count
{
  "query": { "term": { "processed_to_dgraph": true } }
}
```

---

## Schema Application Flow

### When Schema is Applied:

1. **Server Startup** (Automatic)
   - File: [`main.py`](main.py) → `startup_event()`
   - Triggers: `apply_dgraph_schema()`

2. **Manual Processing** (`/process-now`)
   - File: [`api_endpoints.py`](api_endpoints.py) → `process_now()`
   - Triggers: `apply_dgraph_schema()`

3. **Start Monitoring** (`/start`)
   - File: [`api_endpoints.py`](api_endpoints.py) → `start_monitoring()`
   - Triggers: `apply_dgraph_schema()`

4. **Background Monitor** (Every batch)
   - File: [`monitor.py`](monitor.py) → `monitor_and_process()`
   - Triggers: `apply_dgraph_schema()` before each mutation

### Schema Application Function

**File**: [`dgraph_client.py`](dgraph_client.py) (Lines 17-50)

```python
def apply_dgraph_schema(retry: bool = True) -> bool:
    """Apply the schema to Dgraph with retry logic"""
    
    # Read schema from schema.py
    from schema import DGRAPH_SCHEMA
    
    # POST to Dgraph
    response = requests.post(
        f"{DGRAPH_HOST}/alter",  # http://localhost:8180/alter
        data=DGRAPH_SCHEMA,
        timeout=10
    )
    
    # Check response
    if response.status_code == 200:
        logger.info("✅ Schema applied successfully")
        return True
```

**Dgraph Endpoint**: `POST http://localhost:8180/alter`

**Schema Source**: [`schema.py`](schema.py) → `DGRAPH_SCHEMA` variable

---

## Data Processing Pipeline

### Complete Flow with File Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Fetch Unprocessed Documents                            │
├─────────────────────────────────────────────────────────────────┤
│ File: elasticsearch_client.py                                   │
│ Function: fetch_unprocessed_documents()                         │
│                                                                 │
│ Elasticsearch Query:                                            │
│ POST http://localhost:9200/graphdb/_search?scroll=2m           │
│ Body: {                                                         │
│   "query": {                                                    │
│     "bool": {                                                   │
│       "should": [                                               │
│         {"bool": {"must_not": {"exists": {                      │
│           "field": "processed_to_dgraph"}}}},                   │
│         {"term": {"processed_to_dgraph": false}}                │
│       ]                                                         │
│     }                                                           │
│   },                                                            │
│   "size": 100                                                   │
│ }                                                               │
│                                                                 │
│ Returns: List of documents like:                                │
│ [                                                               │
│   {                                                             │
│     "_id": "doc123",                                            │
│     "_source": {                                                │
│       "title": "Case A v. Case B",                              │
│       "year": 2024,                                             │
│       "citations": ["Case C v. D"],                             │
│       "judges": ["Justice Smith"],                              │
│       "court": "Supreme Court",                                 │
│       "court_location": "New Delhi",                            │
│       "court_bench": "Division Bench"                           │
│     }                                                           │
│   }                                                             │
│ ]                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Build Mutation                                         │
├─────────────────────────────────────────────────────────────────┤
│ File: mutation_builder.py                                       │
│ Class: MutationBuilder                                          │
│ Function: build_mutation(documents)                             │
│                                                                 │
│ Process:                                                        │
│ 1. Reset all relation handlers                                 │
│ 2. For each document:                                           │
│    a. Extract judgment data (relations/judgment.py)             │
│    b. Extract citations (relations/citation.py)                 │
│    c. Extract judges (relations/judge.py)                       │
│    d. Extract advocates (relations/advocate.py)                 │
│    e. Extract outcome (relations/outcome.py)                    │
│    f. Extract case duration (relations/case_duration.py)        │
│    g. Extract court (relations/court.py)                        │
│    h. Build complete judgment node with all relationships       │
│ 3. Build all entity nodes                                       │
│ 4. Create final mutation                                        │
│                                                                 │
│ Returns: Mutation object like:                                  │
│ {                                                               │
│   "query": "{ ... }",     # GraphQL queries to find existing    │
│   "set": [ ... ]          # Nodes to create/update              │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Save Mutation to File                                  │
├─────────────────────────────────────────────────────────────────┤
│ File: dgraph_client.py                                          │
│ Function: upload_to_dgraph()                                    │
│                                                                 │
│ Action:                                                         │
│ with open('dgraph_mutation_latest.json', 'w') as f:            │
│     json.dump(mutation, f, indent=2)                            │
│                                                                 │
│ Creates/Overwrites:                                             │
│ - dgraph_mutation_latest.json (single file, always latest)     │
│                                                                 │
│ File Content Example:                                           │
│ {                                                               │
│   "query": "{                                                   │
│     main_1 as var(func: eq(judgment_id, \"J_doc123\"))         │
│     court_abc123 as var(func: eq(name, \"Supreme Court\"))     │
│       @filter(type(Court) AND eq(location, \"New Delhi\"))     │
│   }",                                                           │
│   "set": [                                                      │
│     {                                                           │
│       "uid": "uid(main_1)",                                     │
│       "judgment_id": "J_doc123",                                │
│       "title": "Case A v. Case B",                              │
│       "dgraph.type": "Judgment",                                │
│       "court_heard_in": {"uid": "uid(court_abc123)"}           │
│     },                                                          │
│     {                                                           │
│       "uid": "uid(court_abc123)",                               │
│       "court_id": "court_abc123",                               │
│       "name": "Supreme Court",                                  │
│       "location": "New Delhi",                                  │
│       "bench_type": "Division Bench",                           │
│       "dgraph.type": "Court"                                    │
│     }                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Upload to Dgraph                                       │
├─────────────────────────────────────────────────────────────────┤
│ File: dgraph_client.py                                          │
│ Function: upload_to_dgraph()                                    │
│                                                                 │
│ Dgraph Mutation:                                                │
│ POST http://localhost:8180/mutate?commitNow=true               │
│ Headers: {"Content-Type": "application/json"}                  │
│ Body: <mutation from dgraph_mutation_latest.json>              │
│                                                                 │
│ Response:                                                       │
│ {                                                               │
│   "data": {                                                     │
│     "code": "Success",                                          │
│     "message": "Done",                                          │
│     "uids": {                                                   │
│       "main_1": "0x12345",                                      │
│       "court_abc123": "0x67890"                                 │
│     }                                                           │
│   }                                                             │
│ }                                                               │
│                                                                 │
│ What Dgraph Does:                                               │
│ 1. Executes query block to find existing nodes                 │
│ 2. If node exists → Updates it (upsert)                         │
│ 3. If node doesn't exist → Creates it                           │
│ 4. Creates/updates all relationships                            │
│ 5. Returns UIDs of affected nodes                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Mark Documents as Processed                            │
├─────────────────────────────────────────────────────────────────┤
│ File: elasticsearch_client.py                                   │
│ Function: mark_documents_processed()                            │
│                                                                 │
│ For Each Document:                                              │
│ POST http://localhost:9200/graphdb/_update/{doc_id}            │
│ Body: {                                                         │
│   "doc": {                                                      │
│     "processed_to_dgraph": true,                                │
│     "dgraph_processed_at": "2025-11-12T14:30:00"                │
│   }                                                             │
│ }                                                               │
│                                                                 │
│ Result:                                                         │
│ Document in Elasticsearch now has:                              │
│ {                                                               │
│   "title": "Case A v. Case B",                                  │
│   "processed_to_dgraph": true,  ← MARKED!                       │
│   "dgraph_processed_at": "2025-11-12T14:30:00"                  │
│ }                                                               │
│                                                                 │
│ Next cycle will skip this document!                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Interaction Details

### 1. **Elasticsearch Interactions**

**File**: [`elasticsearch_client.py`](elasticsearch_client.py)

#### Connection
```python
# Function: connect_to_elasticsearch()
# Endpoint: http://localhost:9200
# Action: Ping and verify connection
```

#### Fetch Unprocessed
```python
# Function: fetch_unprocessed_documents()
# Endpoint: POST http://localhost:9200/graphdb/_search?scroll=2m
# Query: {"bool": {"should": [...]}}  # Find where processed_to_dgraph != true
# Returns: List of documents with _id and _source
```

#### Mark Processed
```python
# Function: mark_documents_processed()
# Endpoint: POST http://localhost:9200/graphdb/_update/{doc_id}
# Body: {"doc": {"processed_to_dgraph": true}}
# Action: Update each document to mark as processed
```

#### Get Statistics
```python
# Function: get_elasticsearch_stats()
# Endpoints:
#   - POST http://localhost:9200/graphdb/_count (total)
#   - POST http://localhost:9200/graphdb/_count (with query for processed)
# Returns: {total, processed, unprocessed}
```

---

### 2. **Dgraph Interactions**

**File**: [`dgraph_client.py`](dgraph_client.py)

#### Apply Schema
```python
# Function: apply_dgraph_schema()
# Endpoint: POST http://localhost:8180/alter
# Headers: {"Content-Type": "text/plain"}
# Body: Full schema from schema.py (DGRAPH_SCHEMA variable)
# When: Server startup, /start, /process-now, every monitor cycle
```

#### Upload Mutation
```python
# Function: upload_to_dgraph()
# Endpoint: POST http://localhost:8180/mutate?commitNow=true
# Headers: {"Content-Type": "application/json"}
# Body: Mutation object with query and set blocks
# Action: Upsert nodes and create relationships
```

---

### 3. **Relation Handlers**

**Folder**: `relations/`

Each file handles one entity type:

| File | Entity | Relationship | What It Does |
|------|--------|--------------|--------------|
| `judgment.py` | Judgment | Main node | Extracts title, doc_id, year |
| `citation.py` | Citation | `cites` | Extracts citations list, creates Judgment nodes |
| `judge.py` | Judge | `judged_by` | Extracts judges, creates Judge nodes |
| `advocate.py` | Advocate | `petitioner_represented_by`, `respondant_represented_by` | Extracts advocates, creates Advocate nodes with types |
| `outcome.py` | Outcome | `has_outcome` | Extracts outcome, creates Outcome node |
| `case_duration.py` | CaseDuration | `has_case_duration` | Extracts duration, creates CaseDuration node |
| `court.py` | Court | `court_heard_in` | Extracts court name, location, bench_type, creates Court node |

**Each handler has**:
- `extract_*()` - Get data from Elasticsearch document
- `build_query_parts()` - Build GraphQL queries to find existing nodes
- `build_*_nodes()` - Build node dictionaries for mutation

---

### 4. **Configuration**

**File**: [`config.py`](config.py)

```python
# Elasticsearch
ES_HOST = "http://localhost:9200"
ES_INDEX_NAME = "graphdb"

# Dgraph
DGRAPH_HOST = "http://localhost:8180"

# Monitoring
CHECK_INTERVAL = 30  # seconds
MAX_RETRIES = 20
RETRY_DELAY = 30  # seconds

# Output
OUTPUT_FILE = "dgraph_mutation_latest.json"
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SERVER START                                │
│                    uvicorn main:app --port 8005                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      STARTUP EVENT                                  │
│                      (main.py:43-58)                                │
│                                                                     │
│  1. Apply Schema                                                    │
│     └─> dgraph_client.apply_dgraph_schema()                        │
│         └─> POST http://localhost:8180/alter                       │
│             Body: DGRAPH_SCHEMA from schema.py                      │
│                                                                     │
│  2. Start Background Monitor                                        │
│     └─> asyncio.create_task(monitor_and_process())                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  BACKGROUND MONITOR LOOP                            │
│                   (monitor.py:monitor_and_process)                  │
│                   Runs every 30 seconds                             │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────────────────┐
         │                                                      │
         ↓                                                      │
┌─────────────────────┐                                         │
│ ELASTICSEARCH       │                                         │
│ Port: 9200          │                                         │
│ Index: graphdb      │                                         │
└─────┬───────────────┘                                         │
      │                                                         │
      │ 1. Connect                                              │
      │    elasticsearch_client.connect_to_elasticsearch()      │
      │    Endpoint: http://localhost:9200                      │
      │                                                         │
      │ 2. Fetch Unprocessed                                    │
      │    elasticsearch_client.fetch_unprocessed_documents()   │
      │    Endpoint: POST /graphdb/_search?scroll=2m            │
      │    Query: processed_to_dgraph != true                   │
      │                                                         │
      ↓                                                         │
┌─────────────────────────────────────────┐                     │
│ Documents Found?                        │                     │
│ [                                       │                     │
│   {_id: "doc1", _source: {...}},        │                     │
│   {_id: "doc2", _source: {...}}         │                     │
│ ]                                       │                     │
└─────┬───────────────────────────────────┘                     │
      │                                                         │
      │ 3. Apply Schema (before mutation)                       │
      │    dgraph_client.apply_dgraph_schema()                  │
      │    Endpoint: POST http://localhost:8180/alter           │
      │                                                         │
      │ 4. Build Mutation                                       │
      │    mutation_builder.build_dgraph_mutation()             │
      │    Uses all relation handlers:                          │
      │    ├─> relations/judgment.py                            │
      │    ├─> relations/citation.py                            │
      │    ├─> relations/judge.py                               │
      │    ├─> relations/advocate.py                            │
      │    ├─> relations/outcome.py                             │
      │    ├─> relations/case_duration.py                       │
      │    └─> relations/court.py                               │
      │                                                         │
      ↓                                                         │
┌─────────────────────────────────────────┐                     │
│ MUTATION OBJECT                         │                     │
│ {                                       │                     │
│   "query": "{ ... }",                   │                     │
│   "set": [ ... ]                        │                     │
│ }                                       │                     │
└─────┬───────────────────────────────────┘                     │
      │                                                         │
      │ 5. Save to File                                         │
      │    dgraph_client.upload_to_dgraph()                     │
      │    File: dgraph_mutation_latest.json                    │
      │    Mode: 'w' (overwrite)                                │
      │                                                         │
      │ 6. Upload to Dgraph                                     │
      │    dgraph_client.upload_to_dgraph()                     │
      │    Endpoint: POST http://localhost:8180/mutate          │
      │             ?commitNow=true                             │
      │                                                         │
      ↓                                                         │
┌─────────────────────┐                                         │
│ DGRAPH              │                                         │
│ Port: 8180          │                                         │
└─────┬───────────────┘                                         │
      │                                                         │
      │ Response:                                               │
      │ {                                                       │
      │   "data": {                                             │
      │     "code": "Success",                                  │
      │     "uids": {...}                                       │
      │   }                                                     │
      │ }                                                       │
      │                                                         │
      ↓                                                         │
┌─────────────────────────────────────────┐                     │
│ Success! Mark as Processed              │                     │
│ elasticsearch_client.mark_*_processed() │                     │
│ Endpoint: POST /graphdb/_update/{id}    │                     │
│ Body: {                                 │                     │
│   "doc": {                              │                     │
│     "processed_to_dgraph": true         │                     │
│   }                                     │                     │
│ }                                       │                     │
└─────┬───────────────────────────────────┘                     │
      │                                                         │
      │ 7. Sleep 30 seconds                                     │
      │                                                         │
      └─────────────────────────────────────────────────────────┘
                         (Loop continues)
```

---

## Summary Table

### Endpoints & Their Interactions

| Endpoint | Method | Schema Applied? | ES Read | ES Write | Dgraph Read | Dgraph Write | Files Used |
|----------|--------|----------------|---------|----------|-------------|--------------|------------|
| `/` | GET | ❌ | ❌ | ❌ | ❌ | ❌ | `api_endpoints.py` |
| `/status` | GET | ❌ | ❌ | ❌ | ❌ | ❌ | `api_endpoints.py`, `models.py` |
| `/start` | POST | ✅ | ❌ | ❌ | ❌ | ✅ (schema) | `api_endpoints.py`, `dgraph_client.py`, `monitor.py` |
| `/stop` | POST | ❌ | ❌ | ❌ | ❌ | ❌ | `api_endpoints.py`, `models.py` |
| `/process-now` | POST | ✅ | ✅ | ✅ | ❌ | ✅ (schema + data) | All files |
| `/stats` | GET | ❌ | ✅ | ❌ | ❌ | ❌ | `api_endpoints.py`, `elasticsearch_client.py` |

### Files & Their Purpose

| File | Purpose | Interacts With |
|------|---------|----------------|
| `main.py` | FastAPI entry point, startup logic | All API files |
| `api_endpoints.py` | API route handlers | All processing files |
| `monitor.py` | Background monitoring task | ES, Dgraph clients, mutation builder |
| `elasticsearch_client.py` | ES operations (connect, fetch, mark) | Elasticsearch (port 9200) |
| `dgraph_client.py` | Dgraph operations (schema, upload) | Dgraph (port 8180), `schema.py` |
| `mutation_builder.py` | Orchestrates mutation building | All `relations/*.py` files |
| `schema.py` | Dgraph schema definition | `dgraph_client.py` |
| `config.py` | Configuration settings | All files |
| `models.py` | Data models and state | API and monitor files |
| `relations/*.py` | Entity-specific handlers | `mutation_builder.py` |

---

## Quick Reference Commands

```bash
# Start server
uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# Check status
curl http://localhost:8005/status

# Manual trigger
curl -X POST http://localhost:8005/process-now

# Get statistics
curl http://localhost:8005/stats

# View logs
tail -f dgraph_monitor.log

# View latest mutation
cat dgraph_mutation_latest.json | jq

# Check Elasticsearch
curl http://localhost:9200/graphdb/_count
curl http://localhost:9200/graphdb/_search?pretty

# Check Dgraph
curl http://localhost:8180/health
curl -X POST http://localhost:8180/query -d '{ judgments(func: type(Judgment)) { uid title } }' | jq
```

---

**Version**: 2.0.0  
**Last Updated**: 12 November 2025  
**Author**: Dgraph ETL Pipeline Team
