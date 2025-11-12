#!/usr/bin/env python3
"""
FastAPI Dgraph Monitor - Continuously monitors Elasticsearch for new entries
and automatically pushes them to Dgraph

Features:
- Monitors Elasticsearch for documents where processed_to_dgraph != true
- Automatically generates mutations and uploads to Dgraph
- Marks processed documents in Elasticsearch
- Background task runs continuously
- REST API endpoints for manual control
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from elasticsearch import Elasticsearch
from datetime import datetime
import requests
import hashlib
import json
import time
import asyncio
from typing import Dict, List
import logging

# === Configuration ===
ES_HOST = "http://localhost:9200"
ES_INDEX_NAME = "graphdb"
DGRAPH_HOST = "http://localhost:8180"
OUTPUT_FILE = "dgraph_mutation_latest.json"  # Single file that gets overwritten
CHECK_INTERVAL = 30  # Check every 30 seconds
MAX_RETRIES = 20  # Maximum number of connection retry attempts
RETRY_DELAY = 30  # Initial delay between retries in seconds (will increase exponentially)

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dgraph_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === FastAPI App ===
app = FastAPI(
    title="Dgraph Monitor API",
    description="Monitors Elasticsearch and pushes new entries to Dgraph",
    version="1.0.0"
)

# === Global State ===
monitor_state = {
    "is_running": False,
    "last_check": None,
    "total_processed": 0,
    "last_batch_size": 0,
    "errors": []
}

# === Global tracking to prevent duplicates ===
global_citations = {}
global_judges = {}
global_advocates = {}
global_outcomes = {}
global_case_durations = {}


def get_hash(text: str) -> str:
    """Generate a unique hash for any text"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]


def connect_to_elasticsearch(retry: bool = True) -> Elasticsearch:
    """Connect to Elasticsearch with retry logic"""
    retries = 0
    delay = RETRY_DELAY
    
    while True:
        try:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                raise Exception("Failed to ping Elasticsearch")
            
            if not es.indices.exists(index=ES_INDEX_NAME):
                raise Exception(f"Index '{ES_INDEX_NAME}' does not exist")
            
            logger.info("✅ Connected to Elasticsearch successfully")
            return es
            
        except Exception as e:
            retries += 1
            if not retry or retries >= MAX_RETRIES:
                logger.error(f"❌ Error connecting to Elasticsearch after {retries} attempts: {e}")
                return None
            
            logger.warning(f"⚠️ Failed to connect to Elasticsearch (attempt {retries}/{MAX_RETRIES}): {e}")
            logger.info(f"🔄 Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff


def apply_dgraph_schema(retry: bool = True) -> bool:
    """Apply the schema to Dgraph with retry logic"""
    schema = '''
type Judgment {
  judgment_id
  title
  doc_id
  year
  processed_timestamp
  cites
  judged_by
  petitioner_represented_by
  respondant_represented_by
  has_outcome
  has_case_duration
}

type Judge {
  judge_id
  name
}

type Advocate {
  advocate_id
  name
  advocate_type
}

type Outcome {
  outcome_id
  name
}

type CaseDuration {
  case_duration_id
  duration
}

# Judgment fields
judgment_id: string @index(exact) @upsert .
title: string @index(exact, term, fulltext) @upsert .
doc_id: string @index(exact) @upsert .
year: int @index(int) .
processed_timestamp: datetime @index(hour) .
cites: [uid] @reverse .
judged_by: [uid] @reverse .
petitioner_represented_by: [uid] @reverse .
respondant_represented_by: [uid] @reverse .
has_outcome: uid @reverse .
has_case_duration: uid @reverse .

# Judge fields
judge_id: string @index(exact) @upsert .

# Advocate fields
advocate_id: string @index(exact) @upsert .
advocate_type: string @index(exact) .

# Outcome fields
outcome_id: string @index(exact) @upsert .

# CaseDuration fields
case_duration_id: string @index(exact) @upsert .
duration: string @index(exact, term) .

# Common field (used by Judge, Advocate, Outcome)
name: string @index(exact, term, fulltext) @upsert .
'''
    
    retries = 0
    delay = RETRY_DELAY
    
    while True:
        try:
            response = requests.post(f"{DGRAPH_HOST}/alter", data=schema, timeout=10)
            
            # Check response
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('data', {}).get('code') == 'Success':
                        logger.info("✅ Schema applied successfully")
                        return True
                    else:
                        logger.warning(f"Schema response: {result}")
                        return True  # Consider success even with warnings
                except:
                    # If response is not JSON but status 200, still success
                    logger.info("✅ Schema applied successfully (non-JSON response)")
                    return True
            else:
                raise Exception(f"Schema application failed with status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            retries += 1
            if not retry or retries >= MAX_RETRIES:
                logger.error(f"❌ Error applying schema after {retries} attempts: {e}")
                return False
            
            logger.warning(f"⚠️ Failed to apply Dgraph schema (attempt {retries}/{MAX_RETRIES}): {e}")
            logger.info(f"🔄 Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff


def fetch_unprocessed_documents(es: Elasticsearch) -> List[Dict]:
    """Fetch documents that haven't been processed to Dgraph"""
    try:
        # Query for documents where processed_to_dgraph is not true
        response = es.search(
            index=ES_INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "should": [
                            {"bool": {"must_not": {"exists": {"field": "processed_to_dgraph"}}}},
                            {"term": {"processed_to_dgraph": False}}
                        ]
                    }
                },
                "size": 100
            },
            scroll='2m'
        )
        
        scroll_id = response['_scroll_id']
        documents = response['hits']['hits']
        
        # Continue scrolling if there are more documents
        while len(response['hits']['hits']) > 0:
            response = es.scroll(scroll_id=scroll_id, scroll='2m')
            if len(response['hits']['hits']) == 0:
                break
            documents.extend(response['hits']['hits'])
        
        # Clear scroll
        es.clear_scroll(scroll_id=scroll_id)
        
        logger.info(f"Found {len(documents)} unprocessed documents")
        return documents
    except Exception as e:
        logger.error(f"Error fetching unprocessed documents: {e}")
        return []


def build_dgraph_mutation(documents: List[Dict]) -> Dict:
    """Build single mutation with all data"""
    # Reset global tracking for each batch to avoid variable conflicts
    local_citations = {}
    local_judges = {}
    local_advocates = {}
    local_outcomes = {}
    local_case_durations = {}
    
    all_query_parts = []
    all_set_nodes = []
    
    for idx, doc in enumerate(documents, 1):
        source = doc['_source']
        
        # Extract fields
        title = source.get('title', '').strip()
        doc_id = source.get('doc_id', f"doc_{doc['_id']}").strip()
        year = source.get('year', None)
        citations = source.get('citations', [])
        outcome = source.get('outcome', '').strip()
        case_duration = source.get('case_duration', '').strip()
        judges = source.get('judges', [])
        petitioner_advocates = source.get('petitioner_advocates', [])
        respondant_advocates = source.get('respondant_advocates', [])
        processed_timestamp = source.get('processed_timestamp', None)
        
        # Ensure lists
        if isinstance(citations, str):
            try:
                citations = json.loads(citations)
            except:
                citations = [citations] if citations else []
        elif not isinstance(citations, list):
            citations = []
        
        if not isinstance(judges, list):
            judges = [judges] if judges else []
        if not isinstance(petitioner_advocates, list):
            petitioner_advocates = [petitioner_advocates] if petitioner_advocates else []
        if not isinstance(respondant_advocates, list):
            respondant_advocates = [respondant_advocates] if respondant_advocates else []
        
        # Clean up
        citations = [c.strip() for c in citations if c and c.strip()]
        judges = [j.strip() for j in judges if j and j.strip()]
        petitioner_advocates = [a.strip() for a in petitioner_advocates if a and a.strip()]
        respondant_advocates = [a.strip() for a in respondant_advocates if a and a.strip()]
        
        escaped_title = title.replace('"', '\\"')
        logger.debug(f"Processing document {idx}: {escaped_title[:50]}...")
        
        # Create judgment ID using doc_id for uniqueness
        judgment_id = f"J_{doc_id}"
        all_query_parts.append(f"main_{idx} as var(func: eq(judgment_id, \"{judgment_id}\"))")
        
        # Track citations
        citation_vars = []
        for citation in citations:
            if citation not in local_citations:
                citation_hash = get_hash(citation)
                local_citations[citation] = citation_hash
                escaped_citation = citation.replace('"', '\\"')
                var_name = f"cite_{citation_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(title, \"{escaped_citation}\"))")
            citation_hash = local_citations[citation]
            citation_vars.append(f"cite_{citation_hash}")
        
        # Track judges
        judge_vars = []
        for judge in judges:
            if judge not in local_judges:
                judge_hash = get_hash(judge)
                local_judges[judge] = judge_hash
                escaped_judge = judge.replace('"', '\\"')
                var_name = f"judge_{judge_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_judge}\")) @filter(type(Judge))")
            judge_hash = local_judges[judge]
            judge_vars.append(f"judge_{judge_hash}")
        
        # Track petitioner advocates
        petitioner_advocate_vars = []
        for advocate in petitioner_advocates:
            if advocate not in local_advocates:
                advocate_hash = get_hash(advocate)
                local_advocates[advocate] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) @filter(type(Advocate) AND eq(advocate_type, \"petitioner\"))")
            advocate_hash = local_advocates[advocate]
            petitioner_advocate_vars.append(f"adv_{advocate_hash}")
        
        # Track respondant advocates
        respondant_advocate_vars = []
        for advocate in respondant_advocates:
            advocate_key = f"{advocate}_respondant"
            if advocate_key not in local_advocates:
                advocate_hash = get_hash(advocate_key)
                local_advocates[advocate_key] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                all_query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) @filter(type(Advocate) AND eq(advocate_type, \"respondant\"))")
            advocate_hash = local_advocates[advocate_key]
            respondant_advocate_vars.append(f"adv_{advocate_hash}")
        
        # Track outcome
        outcome_var = None
        if outcome:
            if outcome not in local_outcomes:
                outcome_hash = get_hash(outcome)
                local_outcomes[outcome] = outcome_hash
                escaped_outcome = outcome.replace('"', '\\"')
                outcome_var = f"outcome_{outcome_hash}"
                all_query_parts.append(f"{outcome_var} as var(func: eq(name, \"{escaped_outcome}\")) @filter(type(Outcome))")
            else:
                outcome_hash = local_outcomes[outcome]
                outcome_var = f"outcome_{outcome_hash}"
        
        # Track case duration
        duration_var = None
        if case_duration:
            if case_duration not in local_case_durations:
                duration_hash = get_hash(case_duration)
                local_case_durations[case_duration] = duration_hash
                escaped_duration = case_duration.replace('"', '\\"')
                duration_var = f"duration_{duration_hash}"
                all_query_parts.append(f"{duration_var} as var(func: eq(duration, \"{escaped_duration}\")) @filter(type(CaseDuration))")
            else:
                duration_hash = local_case_durations[case_duration]
                duration_var = f"duration_{duration_hash}"
        
        # Build judgment node
        judgment_node = {
            "uid": f"uid(main_{idx})",
            "judgment_id": judgment_id,
            "title": title,
            "doc_id": doc_id,
            "dgraph.type": "Judgment"
        }
        
        if year is not None:
            judgment_node["year"] = year
        
        if processed_timestamp:
            judgment_node["processed_timestamp"] = processed_timestamp
        
        # Add relationships
        if citation_vars:
            judgment_node["cites"] = [{"uid": f"uid({var})"} for var in citation_vars]
        if judge_vars:
            judgment_node["judged_by"] = [{"uid": f"uid({var})"} for var in judge_vars]
        if petitioner_advocate_vars:
            judgment_node["petitioner_represented_by"] = [{"uid": f"uid({var})"} for var in petitioner_advocate_vars]
        if respondant_advocate_vars:
            judgment_node["respondant_represented_by"] = [{"uid": f"uid({var})"} for var in respondant_advocate_vars]
        if outcome_var:
            judgment_node["has_outcome"] = {"uid": f"uid({outcome_var})"}
        if duration_var:
            judgment_node["has_case_duration"] = {"uid": f"uid({duration_var})"}
        
        all_set_nodes.append(judgment_node)
    
    # Add all citation nodes
    for citation, citation_hash in local_citations.items():
        all_set_nodes.append({
            "uid": f"uid(cite_{citation_hash})",
            "title": citation,
            "dgraph.type": "Judgment"
        })
    
    # Add all judge nodes
    for judge, judge_hash in local_judges.items():
        all_set_nodes.append({
            "uid": f"uid(judge_{judge_hash})",
            "judge_id": f"judge_{judge_hash}",
            "name": judge,
            "dgraph.type": "Judge"
        })
    
    # Add all advocate nodes
    for advocate_key, advocate_hash in local_advocates.items():
        advocate_name = advocate_key.replace("_respondant", "")
        advocate_type = "respondant" if "_respondant" in advocate_key else "petitioner"
        all_set_nodes.append({
            "uid": f"uid(adv_{advocate_hash})",
            "advocate_id": f"adv_{advocate_hash}",
            "name": advocate_name,
            "advocate_type": advocate_type,
            "dgraph.type": "Advocate"
        })
    
    # Add all outcome nodes
    for outcome, outcome_hash in local_outcomes.items():
        all_set_nodes.append({
            "uid": f"uid(outcome_{outcome_hash})",
            "outcome_id": f"outcome_{outcome_hash}",
            "name": outcome,
            "dgraph.type": "Outcome"
        })
    
    # Add all case duration nodes
    for duration, duration_hash in local_case_durations.items():
        all_set_nodes.append({
            "uid": f"uid(duration_{duration_hash})",
            "case_duration_id": f"duration_{duration_hash}",
            "duration": duration,
            "dgraph.type": "CaseDuration"
        })
    
    # Create final mutation
    final_mutation = {
        "query": "{\n  " + "\n  ".join(all_query_parts) + "\n}",
        "set": all_set_nodes
    }
    
    logger.info(f"Mutation built: {len(all_set_nodes)} total nodes")
    return final_mutation


def upload_to_dgraph(mutation: Dict, retry: bool = True) -> bool:
    """Save mutation to file and upload to Dgraph with retry logic"""
    try:
        # Save to single file (overwrites each time)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(mutation, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved mutation to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Error saving mutation to file: {e}")
        # Continue even if file save fails
    
    retries = 0
    delay = RETRY_DELAY
    
    while True:
        try:
            # Upload to Dgraph
            response = requests.post(
                f"{DGRAPH_HOST}/mutate?commitNow=true",
                headers={"Content-Type": "application/json"},
                json=mutation,
                timeout=30
            )
            
            logger.info(f"Dgraph response status: {response.status_code}")
            
            # Check if response is successful
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"Dgraph response: {result}")
                    
                    # Check if it's a successful mutation
                    if result.get('data', {}).get('code') == 'Success' or 'uids' in result.get('data', {}):
                        logger.info("✅ Data uploaded to Dgraph successfully")
                        return True
                    else:
                        logger.warning(f"Unexpected Dgraph response: {result}")
                        return True  # Still consider it success if status 200
                except ValueError as json_err:
                    logger.warning(f"Response is not JSON: {response.text[:200]}")
                    # If status 200 but not JSON, still consider success
                    return True
            else:
                raise Exception(f"Dgraph returned status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            retries += 1
            if not retry or retries >= MAX_RETRIES:
                logger.error(f"❌ Error uploading to Dgraph after {retries} attempts: {e}")
                return False
            
            logger.warning(f"⚠️ Failed to upload to Dgraph (attempt {retries}/{MAX_RETRIES}): {e}")
            logger.info(f"🔄 Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 5  # Exponential backoff


def mark_documents_processed(es: Elasticsearch, documents: List[Dict]) -> bool:
    """Mark documents as processed in Elasticsearch"""
    try:
        for doc in documents:
            es.update(
                index=ES_INDEX_NAME,
                id=doc['_id'],
                body={
                    "doc": {
                        "processed_to_dgraph": True,
                        "dgraph_processed_at": datetime.utcnow().isoformat()
                    }
                }
            )
        logger.info(f"Marked {len(documents)} documents as processed")
        return True
    except Exception as e:
        logger.error(f"Error marking documents as processed: {e}")
        return False


async def monitor_and_process():
    """Background task that continuously monitors Elasticsearch"""
    logger.info("🔄 Starting continuous monitoring...")
    
    while monitor_state["is_running"]:
        try:
            monitor_state["last_check"] = datetime.utcnow().isoformat()
            
            # Connect to Elasticsearch with retry
            es = connect_to_elasticsearch(retry=True)
            if not es:
                logger.error("❌ Failed to connect to Elasticsearch after retries, will retry in next cycle...")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            # Fetch unprocessed documents
            documents = fetch_unprocessed_documents(es)
            
            if documents:
                logger.info(f"📝 Processing {len(documents)} new documents...")
                
                # Ensure schema is applied before mutation (with retry)
                if not apply_dgraph_schema(retry=True):
                    logger.error("❌ Failed to apply Dgraph schema after retries, will retry in next cycle...")
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue
                
                # Build mutation
                mutation = build_dgraph_mutation(documents)
                
                # Upload to Dgraph (with retry)
                if upload_to_dgraph(mutation, retry=True):
                    # Mark as processed
                    if mark_documents_processed(es, documents):
                        monitor_state["total_processed"] += len(documents)
                        monitor_state["last_batch_size"] = len(documents)
                        logger.info(f"✅ Successfully processed {len(documents)} documents")
                    else:
                        logger.error("❌ Failed to mark documents as processed")
                else:
                    logger.error("❌ Failed to upload to Dgraph after retries")
            else:
                logger.debug("📭 No new documents to process")
            
            # Wait before next check
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            error_msg = f"Error in monitoring loop: {e}"
            logger.error(error_msg)
            monitor_state["errors"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            # Keep only last 10 errors
            monitor_state["errors"] = monitor_state["errors"][-10:]
            await asyncio.sleep(CHECK_INTERVAL)
    
    logger.info("🛑 Monitoring stopped")


# === API Endpoints ===

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Dgraph Monitor API",
        "version": "1.0.0",
        "endpoints": {
            "/status": "Get current monitoring status",
            "/start": "Start continuous monitoring",
            "/stop": "Stop monitoring",
            "/process-now": "Process unprocessed documents immediately",
            "/stats": "Get processing statistics"
        }
    }


@app.get("/status")
async def get_status():
    """Get current monitoring status"""
    return {
        "is_running": monitor_state["is_running"],
        "last_check": monitor_state["last_check"],
        "total_processed": monitor_state["total_processed"],
        "last_batch_size": monitor_state["last_batch_size"],
        "check_interval_seconds": CHECK_INTERVAL,
        "recent_errors": monitor_state["errors"][-5:]
    }


@app.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start continuous monitoring"""
    if monitor_state["is_running"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Monitoring is already running"}
        )
    
    # Apply schema first (with retry, but don't fail if Dgraph is down - retry in background)
    logger.info("🔄 Applying Dgraph schema...")
    schema_applied = apply_dgraph_schema(retry=True)
    
    # Start monitoring even if schema fails - it will retry in the background loop
    monitor_state["is_running"] = True
    background_tasks.add_task(monitor_and_process)
    
    logger.info("✅ Monitoring started")
    
    if not schema_applied:
        return {
            "message": "Monitoring started (Dgraph connection pending - will retry automatically)",
            "check_interval_seconds": CHECK_INTERVAL,
            "warning": "Dgraph schema could not be applied yet, but monitoring will retry automatically"
        }
    
    return {
        "message": "Monitoring started successfully",
        "check_interval_seconds": CHECK_INTERVAL
    }


@app.post("/stop")
async def stop_monitoring():
    """Stop monitoring"""
    if not monitor_state["is_running"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Monitoring is not running"}
        )
    
    monitor_state["is_running"] = False
    logger.info("Monitoring stopped by user request")
    
    return {
        "message": "Monitoring stopped successfully",
        "total_processed": monitor_state["total_processed"]
    }


@app.post("/process-now")
async def process_now():
    """Process unprocessed documents immediately (manual trigger)"""
    try:
        logger.info("🚀 Manual processing triggered")
        
        # Connect to Elasticsearch with retry
        es = connect_to_elasticsearch(retry=True)
        if not es:
            raise HTTPException(status_code=500, detail="Failed to connect to Elasticsearch after retries")
        
        # Fetch unprocessed documents
        documents = fetch_unprocessed_documents(es)
        
        if not documents:
            return {
                "message": "No unprocessed documents found",
                "processed_count": 0
            }
        
        # Apply schema with retry
        if not apply_dgraph_schema(retry=True):
            raise HTTPException(status_code=500, detail="Failed to apply Dgraph schema after retries")
        
        # Build mutation
        mutation = build_dgraph_mutation(documents)
        
        # Upload to Dgraph with retry
        if not upload_to_dgraph(mutation, retry=True):
            raise HTTPException(status_code=500, detail="Failed to upload to Dgraph after retries")
        
        # Mark as processed
        if not mark_documents_processed(es, documents):
            raise HTTPException(status_code=500, detail="Failed to mark documents as processed")
        
        monitor_state["total_processed"] += len(documents)
        
        return {
            "message": "Processing completed successfully",
            "processed_count": len(documents),
            "total_nodes": len(mutation["set"])
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Error in manual processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get detailed statistics"""
    try:
        es = connect_to_elasticsearch()
        if not es:
            raise HTTPException(status_code=500, detail="Failed to connect to Elasticsearch")
        
        # Count total documents
        total_count = es.count(index=ES_INDEX_NAME)['count']
        
        # Count processed documents
        processed_count = es.count(
            index=ES_INDEX_NAME,
            body={
                "query": {
                    "term": {"processed_to_dgraph": True}
                }
            }
        )['count']
        
        # Count unprocessed documents
        unprocessed_count = total_count - processed_count
        
        return {
            "elasticsearch": {
                "total_documents": total_count,
                "processed_documents": processed_count,
                "unprocessed_documents": unprocessed_count
            },
            "monitor": {
                "is_running": monitor_state["is_running"],
                "total_processed_by_monitor": monitor_state["total_processed"],
                "last_check": monitor_state["last_check"],
                "last_batch_size": monitor_state["last_batch_size"]
            },
            "dgraph": {
                "citations_tracked": len(global_citations),
                "judges_tracked": len(global_judges),
                "advocates_tracked": len(global_advocates),
                "outcomes_tracked": len(global_outcomes),
                "case_durations_tracked": len(global_case_durations)
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("=" * 70)
    logger.info("🚀 Dgraph Monitor API Started")
    logger.info("=" * 70)
    logger.info(f"Elasticsearch: {ES_HOST}")
    logger.info(f"Dgraph: {DGRAPH_HOST}")
    logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Max Retries: {MAX_RETRIES}")
    logger.info(f"Initial Retry Delay: {RETRY_DELAY} seconds (exponential backoff)")
    logger.info("=" * 70)
    
    # Auto-start monitoring (even if Dgraph/ES is down - will retry in background)
    logger.info("🔄 Auto-starting monitoring with automatic retry...")
    monitor_state["is_running"] = True
    asyncio.create_task(monitor_and_process())
    logger.info("✅ Monitoring task started! Will automatically retry connections if services are down.")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    monitor_state["is_running"] = False
    logger.info("=" * 70)
    logger.info("🛑 Dgraph Monitor API Stopped")
    logger.info(f"Total documents processed: {monitor_state['total_processed']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
