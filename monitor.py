#!/usr/bin/env python3
"""
Background monitoring task
"""

import asyncio
import logging
from datetime import datetime

from config import CHECK_INTERVAL
from models import monitor_state
from elasticsearch_client import connect_to_elasticsearch, fetch_unprocessed_documents, mark_documents_with_per_doc_entities
from dgraph_client import apply_dgraph_schema, upload_to_dgraph
from mutation_builder import build_dgraph_mutation
from entity_detector import detect_entities_in_batch

logger = logging.getLogger(__name__)


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
                
                # Detect which entities exist in each document
                doc_entities = detect_entities_in_batch(documents)
                
                # Build mutation
                mutation = build_dgraph_mutation(documents)
                
                # Upload to Dgraph (with retry)
                if upload_to_dgraph(mutation, retry=True):
                    # Mark as processed with per-document entity tracking
                    # Only mark entities that actually exist in each document
                    if mark_documents_with_per_doc_entities(es, doc_entities):
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
