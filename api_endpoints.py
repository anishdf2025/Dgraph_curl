#!/usr/bin/env python3
"""
FastAPI route handlers
"""

import asyncio
import logging
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from config import CHECK_INTERVAL
from models import monitor_state, global_citations, global_judges, global_advocates, global_outcomes, global_case_durations, global_courts
from elasticsearch_client import connect_to_elasticsearch, fetch_unprocessed_documents, mark_documents_with_per_doc_entities, get_elasticsearch_stats
from dgraph_client import apply_dgraph_schema, upload_to_dgraph
from mutation_builder import build_dgraph_mutation
from monitor import monitor_and_process
from entity_detector import detect_entities_in_batch

logger = logging.getLogger(__name__)


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
        
        # Detect which entities exist in each document
        doc_entities = detect_entities_in_batch(documents)
        
        # Build mutation
        mutation = build_dgraph_mutation(documents)
        
        # Upload to Dgraph with retry
        if not upload_to_dgraph(mutation, retry=True):
            raise HTTPException(status_code=500, detail="Failed to upload to Dgraph after retries")
        
        # Mark as processed with per-document entity tracking
        # Only mark entities that actually exist in each document
        if not mark_documents_with_per_doc_entities(es, doc_entities):
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


async def get_stats():
    """Get detailed statistics"""
    try:
        es = connect_to_elasticsearch()
        if not es:
            raise HTTPException(status_code=500, detail="Failed to connect to Elasticsearch")
        
        # Get Elasticsearch stats
        es_stats = get_elasticsearch_stats(es)
        
        return {
            "elasticsearch": es_stats,
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
                "case_durations_tracked": len(global_case_durations),
                "courts_tracked": len(global_courts)
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
