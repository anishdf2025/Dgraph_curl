# 🚀 Dgraph ETL Pipeline - Complete Documentation

**Continuous Elasticsearch to Dgraph ETL Pipeline with Modular Relations Architecture**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Modular Relations Structure](#modular-relations-structure)
5. [API Endpoints](#api-endpoints)
6. [Debugging Guide](#debugging-guide)
7. [Adding New Relations](#adding-new-relations)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This system continuously monitors Elasticsearch for new legal judgment documents and automatically pushes them to Dgraph as a graph database with proper relationships.

### ✨ Features

- ✅ **Automatic Monitoring** - Checks Elasticsearch every 30 seconds
- ✅ **Smart Detection** - Only processes documents where `processed_to_dgraph != true`
- ✅ **Modular Architecture** - Each entity relation in separate file
- ✅ **Automatic Schema Application** - Applies Dgraph schema before mutations
- ✅ **Duplicate Prevention** - Hash-based deduplication for all entities
- ✅ **REST API** - Full control via HTTP endpoints
- ✅ **Background Processing** - Non-blocking continuous monitoring
- ✅ **Error Handling** - Resilient to failures with retry logic
- ✅ **Easy to Debug** - Isolated components per relation

### 🏛️ Supported Entities

- **Judgment** (Title) - Main node
- **Citations** - Other cases cited
- **Judges** - Presiding judges
- **Advocates** - Petitioner and respondant lawyers
- **Outcomes** - Case outcomes
- **Case Durations** - Time period of case
- **Courts** - Court where case was heard

---

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Services Running

Ensure these services are running:
- **Elasticsearch**: `http://localhost:9200`
- **Dgraph**: `http://localhost:8180`

### 3. Start the API

```bash
uvicorn fastapi_dgraph_monitor:app --host 0.0.0.0 --port 8005 --reload
```

The API will start on `http://localhost:8005` and **automatically begin monitoring**.

### 4. Check Status

```bash
curl http://localhost:8005/status
```

### 5. Test with Sample Data

```bash
curl -X POST "http://localhost:9200/graphdb/_doc/test_1" -H 'Content-Type: application/json' -d'
{
  "title": "Test Case v. Example Corp",
  "doc_id": "test_1",
  "year": 2025,
  "citations": ["Previous Case (2024) 1 SCC 100"],
  "judges": ["Justice Test"],
  "petitioner_advocates": ["Mr. Advocate"],
  "respondant_advocates": ["Ms. Defense"],
  "outcome": "Allowed",
  "case_duration": "2025-01-01 to 2025-06-01",
  "court": "Supreme Court of India",
  "court_location": "New Delhi"
}
'
```

Within 30 seconds, the document will be automatically processed!

---

## Architecture

### 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Application                     │
│                    (main.py)                            │
└──────────────────────┬──────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   Monitor   │ │    API     │ │  Dgraph    │
│(monitor.py) │ │ Endpoints  │ │  Client    │
└──────┬──────┘ └────────────┘ └────────────┘
       │
┌──────▼──────┐
│Elasticsearch│
│   Client    │
└──────┬──────┘
       │
┌──────▼──────┐
│  Mutation   │
│   Builder   │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│           relations/ Module                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Judgment  │  │Citation  │  │  Judge   │  │
│  │  (5KB)   │  │  (3KB)   │  │  (3KB)   │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Advocate  │  │ Outcome  │  │  Case    │  │
│  │  (5KB)   │  │  (3KB)   │  │Duration  │  │
│  └──────────┘  └──────────┘  │  (3KB)   │  │
│  ┌──────────┐                └──────────┘  │
│  │  Court   │                               │
│  │  (4KB)   │                               │
│  └──────────┘                               │
└──────────────────────────────────────────────┘
```

### 📁 File Structure

```
Dgraph_curl/
├── relations/                      # Modular entity handlers
│   ├── __init__.py                 # Module exports
│   ├── judgment.py                 # Main Title node
│   ├── citation.py                 # Citation relation
│   ├── judge.py                    # Judge relation
│   ├── advocate.py                 # Advocate relation
│   ├── outcome.py                  # Outcome relation
│   ├── case_duration.py            # Case duration relation
│   └── court.py                    # Court relation
│
├── mutation_builder.py             # Orchestrates all relation handlers
├── monitor.py                      # Background monitoring task
├── elasticsearch_client.py         # ES operations
├── dgraph_client.py                # Dgraph operations
├── api_endpoints.py                # FastAPI route handlers
├── main.py                         # FastAPI entry point
│
├── config.py                       # Configuration settings
├── schema.py                       # Schema definitions
├── models.py                       # Data models
│
├── fastapi_dgraph_monitor.py       # Original monolithic (backup)
├── schema_improved.sh              # Dgraph schema script
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

### 🔄 Data Flow

```
Elasticsearch (Port 9200)
         ↓
    Monitor Task (every 30s)
         ↓
  Detect unprocessed documents
         ↓
    Mutation Builder
         ↓
  ┌──────────────────────┐
  │  Process Relations:  │
  │  1. Judgment         │
  │  2. Citations        │
  │  3. Judges           │
  │  4. Advocates        │
  │  5. Outcomes         │
  │  6. Case Durations   │
  │  7. Courts           │
  └──────────────────────┘
         ↓
   Build Mutation
         ↓
   Upload to Dgraph (Port 8180)
         ↓
   Mark as processed in ES
```

---

## Modular Relations Structure

### 🎯 Central Node: Judgment (Title)

All entities connect to the **Judgment** node as the central hub:

```
                    ┌──────────────────┐
                    │    JUDGMENT      │
                    │    (Title)       │
                    └────────┬─────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
┌─────▼─────┐         ┌──────▼──────┐       ┌──────▼──────┐
│ Citation  │         │   Judge     │       │  Advocate   │
│  [cites]  │         │ [judged_by] │       │ [petitioner_│
└───────────┘         └─────────────┘       │  respondant]│
                                            └─────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
┌─────▼─────┐         ┌──────▼──────┐       ┌──────▼──────┐
│  Outcome  │         │CaseDuration │       │   Court     │
│[has_outcome]        │[has_case_   │       │[court_heard_│
└───────────┘         │  duration]  │       │     in]     │
                      └─────────────┘       └─────────────┘
```

### 📊 Relationship Mapping

| Relation File | Edge Name | From | To | Cardinality |
|---------------|-----------|------|-----|-------------|
| `citation.py` | `cites` | Judgment | Judgment | One-to-Many |
| `judge.py` | `judged_by` | Judgment | Judge | One-to-Many |
| `advocate.py` | `petitioner_represented_by` | Judgment | Advocate | One-to-Many |
| `advocate.py` | `respondant_represented_by` | Judgment | Advocate | One-to-Many |
| `outcome.py` | `has_outcome` | Judgment | Outcome | One-to-One |
| `case_duration.py` | `has_case_duration` | Judgment | CaseDuration | One-to-One |
| `court.py` | `court_heard_in` | Judgment | Court | One-to-One |

### 📝 Relation Files

#### 1. **judgment.py** - Main Node Handler

**Purpose**: Handles the main Judgment (Title) node

**Key Methods**:
```python
extract_judgment_data(doc, idx)      # Extract judgment fields
build_query_part(judgment_data)       # Build query for judgment lookup
build_judgment_node(...)              # Build complete judgment node with all relations
```

**Fields**:
- `judgment_id` - Unique identifier
- `title` - Case name (main identifier)
- `doc_id` - Document ID (without doc_ prefix)
- `year` - Year of judgment

---

#### 2. **citation.py** - Citation Relation

**Relationship**: `Judgment --[cites]--> Judgment`

**Purpose**: Handles citation relationships between judgments

**Key Methods**:
```python
extract_citations(source)             # Extract citations list
build_query_parts(citations)          # Build queries for each citation
build_citation_nodes()                # Build all citation nodes
```

---

#### 3. **judge.py** - Judge Relation

**Relationship**: `Judgment --[judged_by]--> Judge`

**Purpose**: Handles judge relationships with judgments

**Key Methods**:
```python
extract_judges(source)                # Extract judges list
build_query_parts(judges)             # Build queries for each judge
build_judge_nodes()                   # Build all judge nodes
```

---

#### 4. **advocate.py** - Advocate Relation

**Relationships**: 
- `Judgment --[petitioner_represented_by]--> Advocate`
- `Judgment --[respondant_represented_by]--> Advocate`

**Purpose**: Handles advocate relationships (2 types)

**Key Methods**:
```python
extract_advocates(source)             # Extract both advocate types
build_query_parts(pet_advs, resp_advs) # Build queries with types
build_advocate_nodes()                # Build all advocate nodes
```

---

#### 5. **outcome.py** - Outcome Relation

**Relationship**: `Judgment --[has_outcome]--> Outcome`

**Purpose**: Handles outcome relationships

**Key Methods**:
```python
extract_outcome(source)               # Extract outcome
build_query_parts(outcome)            # Build query for outcome
build_outcome_nodes()                 # Build all outcome nodes
```

---

#### 6. **case_duration.py** - Case Duration Relation

**Relationship**: `Judgment --[has_case_duration]--> CaseDuration`

**Purpose**: Handles case duration relationships

**Key Methods**:
```python
extract_case_duration(source)         # Extract case duration
build_query_parts(case_duration)      # Build query for duration
build_case_duration_nodes()           # Build all duration nodes
```

---

#### 7. **court.py** - Court Relation

**Relationship**: `Judgment --[court_heard_in]--> Court`

**Purpose**: Handles court relationships

**Key Methods**:
```python
extract_court(source)                 # Extract court name and location
build_query_parts(name, location)     # Build query for court
build_court_nodes()                   # Build all court nodes
```

---

## API Endpoints

### 📊 GET /status

Check monitor status

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

---

### ▶️ POST /start

Start monitoring (already starts automatically)

```bash
curl -X POST http://localhost:8005/start
```

---

### ⏹️ POST /stop

Stop monitoring

```bash
curl -X POST http://localhost:8005/stop
```

---

### ⚡ POST /process-now

Force immediate processing

```bash
curl -X POST http://localhost:8005/process-now
```

---

### 📈 GET /stats

Get detailed statistics

```bash
curl http://localhost:8005/stats
```

**Response**:
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
    "last_check": "2025-11-12T14:30:00",
    "last_batch_size": 5
  },
  "dgraph": {
    "citations_tracked": 35,
    "judges_tracked": 42,
    "advocates_tracked": 58,
    "outcomes_tracked": 2,
    "case_durations_tracked": 18,
    "courts_tracked": 5
  }
}
```

---

### 📖 GET /docs

Interactive API documentation (Swagger UI)

Visit: `http://localhost:8005/docs`

---

## Debugging Guide

### 🐛 Problem: "Citations not being created"

**Solution**:
1. Open `relations/citation.py` (only ~100 lines)
2. Add logging in `extract_citations()`:
   ```python
   logger.debug(f"🔍 Raw citations: {citations}")
   logger.debug(f"✅ Cleaned citations: {cleaned}")
   ```
3. Check logs: `tail -f dgraph_monitor.log`
4. Fix the specific issue
5. Other relations are unaffected! ✅

---

### 🐛 Problem: "Judge query failing"

**Solution**:
1. Open `relations/judge.py`
2. Check the exact query being built in `build_query_parts()`
3. Add debug logging:
   ```python
   logger.debug(f"Judge query: {query_parts}")
   ```
4. Fix it
5. Done! Other relations work fine ✅

---

### 🐛 Debug Workflow

```
1. Identify the relation → e.g., "judges not showing"
2. Open specific file → relations/judge.py
3. Add logging → logger.debug(...)
4. Check logs → tail -f dgraph_monitor.log
5. Fix and test → Only that file affected!
```

---

### 📊 Check Statistics Per Relation

```bash
curl http://localhost:8005/stats | jq .dgraph

# Shows counts per relation:
{
  "citations_tracked": 10,
  "judges_tracked": 15,
  "advocates_tracked": 20,
  "outcomes_tracked": 2,
  "case_durations_tracked": 8,
  "courts_tracked": 5
}
```

---

## Adding New Relations

Want to add a new entity? (e.g., State, Law, etc.)

### Step-by-Step Guide

#### 1. Create Relation File

```bash
# Create new file
touch relations/state.py
```

#### 2. Implement Handler

```python
#!/usr/bin/env python3
"""
State Relation Handler
Handles: Judgment --[filed_in]--> State
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class StateRelation:
    def __init__(self):
        self.local_states = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        self.local_states = {}
    
    def extract_state(self, source: Dict[str, Any]) -> Optional[str]:
        state = source.get('state', '').strip()
        return state if state else None
    
    def build_query_parts(self, state: str) -> Tuple[List[str], Optional[str]]:
        if not state:
            return [], None
        
        query_parts = []
        state_var = None
        
        if state not in self.local_states:
            state_hash = self.get_hash(state)
            self.local_states[state] = state_hash
            escaped_state = state.replace('"', '\\"')
            state_var = f"state_{state_hash}"
            query_parts.append(
                f"{state_var} as var(func: eq(name, \"{escaped_state}\")) "
                f"@filter(type(State))"
            )
        else:
            state_hash = self.local_states[state]
            state_var = f"state_{state_hash}"
        
        return query_parts, state_var
    
    def build_state_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for state, state_hash in self.local_states.items():
            nodes.append({
                "uid": f"uid(state_{state_hash})",
                "state_id": f"state_{state_hash}",
                "name": state,
                "dgraph.type": "State"
            })
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        return {"total_states": len(self.local_states)}
```

#### 3. Update `relations/__init__.py`

```python
from .state import StateRelation

__all__ = [
    # ...existing...
    'StateRelation'
]
```

#### 4. Update `mutation_builder.py`

```python
from relations import (
    # ...existing...
    StateRelation
)

class MutationBuilder:
    def __init__(self):
        # ...existing handlers...
        self.state_handler = StateRelation()
    
    def build_mutation(self, documents):
        # Reset
        self.state_handler.reset()
        
        # Process
        for idx, doc in enumerate(documents, 1):
            source = doc['_source']
            
            # ...existing code...
            
            # Add State processing
            state = self.state_handler.extract_state(source)
            state_queries, state_var = self.state_handler.build_query_parts(state)
            all_query_parts.extend(state_queries)
            
            # Add to judgment node
            judgment_node = self.judgment_handler.build_judgment_node(
                # ...existing params...
                state_var=state_var
            )
        
        # Build nodes
        all_set_nodes.extend(self.state_handler.build_state_nodes())
```

#### 5. Update Schema

```bash
# Add to schema.py or schema_improved.sh
type State {
  state_id
  name
}

filed_in: uid @reverse .
state_id: string @index(exact) @upsert .
```

**Done!** ✅ Your new relation is ready.

---

## Configuration

### Environment Variables

Edit `config.py`:

```python
ES_HOST = "http://localhost:9200"      # Elasticsearch host
ES_INDEX_NAME = "graphdb"              # ES index name
DGRAPH_HOST = "http://localhost:8180"  # Dgraph host
OUTPUT_FILE = "dgraph_mutation_latest.json"  # Output file
CHECK_INTERVAL = 30                    # Check interval (seconds)
MAX_RETRIES = 20                       # Max retry attempts
RETRY_DELAY = 30                       # Retry delay (seconds)
```

### Schema Configuration

The schema is auto-applied on startup. To manually apply:

```bash
bash schema_improved.sh
```

---

## Troubleshooting

### Monitor not detecting new documents

**Check Elasticsearch**:
```bash
curl http://localhost:9200/_cluster/health
```

**Check unprocessed documents**:
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

**Check logs**:
```bash
tail -f dgraph_monitor.log
```

---

### Dgraph connection failed

**Verify Dgraph is running**:
```bash
curl http://localhost:8180/health
```

**Check Dgraph logs**:
```bash
# Check your Dgraph logs location
```

---

### API not starting

**Check if port is available**:
```bash
lsof -i :8005
```

**Install dependencies**:
```bash
pip install -r requirements.txt
```

---

## Performance

- **Check Interval**: 30 seconds (configurable)
- **Batch Size**: Up to 100 documents per batch
- **Memory**: Minimal (uses scroll API)
- **CPU**: Low (async operations)

---

## Security Considerations

For production:

1. **Add Authentication** - Use FastAPI security features
2. **Use HTTPS** - Configure SSL/TLS
3. **Firewall** - Restrict access to port 8005
4. **Environment Variables** - Store credentials securely
5. **Rate Limiting** - Add rate limiting middleware

---

## 🎯 Benefits of This Architecture

| Aspect | Before (Monolithic) | After (Modular) |
|--------|---------------------|-----------------|
| **Code Size** | 883 lines in 1 file | ~100 lines per file |
| **Debugging** | Search 400+ lines | Check specific file |
| **Adding Relations** | Modify large function | Create new file |
| **Testing** | Test everything | Test per relation |
| **Understanding** | Read 400 lines | Read 100 lines |
| **Maintenance** | High coupling | Low coupling |

---

## 📚 Summary

This system provides:

✅ **Automatic ETL** - Continuous Elasticsearch → Dgraph pipeline
✅ **Modular Design** - Each relation in its own file
✅ **Easy Debugging** - Isolated components
✅ **Scalable** - Add new relations easily
✅ **Well Documented** - Complete guide in one place
✅ **Production Ready** - Error handling, retry logic, logging

---

## 📖 Quick Reference

### Common Commands

```bash
# Start server
uvicorn fastapi_dgraph_monitor:app --host 0.0.0.0 --port 8005 --reload

# Check status
curl http://localhost:8005/status

# Get stats
curl http://localhost:8005/stats

# Force processing
curl -X POST http://localhost:8005/process-now

# View logs
tail -f dgraph_monitor.log
```

### File Locations

- **Relations**: `relations/*.py`
- **Mutation Builder**: `mutation_builder.py`
- **Monitor**: `monitor.py`
- **API**: `api_endpoints.py`
- **Config**: `config.py`
- **Schema**: `schema.py`, `schema_improved.sh`
- **Logs**: `dgraph_monitor.log`
- **Output**: `dgraph_mutation_latest.json`

---

## 💡 Support

For issues or questions:
- Check logs: `dgraph_monitor.log`
- View stats: `curl http://localhost:8005/stats`
- Check status: `curl http://localhost:8005/status`
- Open specific relation file for debugging

---

**Version**: 1.0.0  
**Last Updated**: 12 November 2025  
**License**: MIT
