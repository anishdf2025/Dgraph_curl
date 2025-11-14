#!/usr/bin/env python3
"""
Elasticsearch client operations
"""

from elasticsearch import Elasticsearch
from typing import Dict, List
import time
import logging
from datetime import datetime

from config import ES_HOST, ES_INDEX_NAME, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


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


def fetch_unprocessed_documents(es: Elasticsearch, entity_type: str = None) -> List[Dict]:
    """
    Fetch documents that haven't been processed to Dgraph
    
    Args:
        es: Elasticsearch client
        entity_type: Specific entity type to check (e.g., 'court_bench', 'acts')
                    If None, fetches documents with no processing at all
    """
    try:
        # Build query based on entity_type
        if entity_type:
            # Query for documents where specific entity is not processed
            query = {
                "bool": {
                    "should": [
                        {"bool": {"must_not": {"exists": {"field": f"processed_entities.{entity_type}"}}}},
                        {"term": {f"processed_entities.{entity_type}": False}}
                    ]
                }
            }
        else:
            # Query for documents where processed_to_dgraph is not true
            query = {
                "bool": {
                    "should": [
                        {"bool": {"must_not": {"exists": {"field": "processed_to_dgraph"}}}},
                        {"term": {"processed_to_dgraph": False}}
                    ]
                }
            }
        
        response = es.search(
            index=ES_INDEX_NAME,
            body={
                "query": query,
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


def mark_documents_processed(es: Elasticsearch, documents: List[Dict], entity_types: List[str] = None) -> bool:
    """
    Mark documents as processed in Elasticsearch with granular entity tracking
    
    Args:
        es: Elasticsearch client
        documents: List of processed documents
        entity_types: List of entity types that were processed (e.g., ['judgment', 'citations', 'court_bench'])
                     If None, marks entire document as processed (legacy mode)
    """
    try:
        timestamp = datetime.utcnow().isoformat()
        
        for doc in documents:
            if entity_types:
                # Granular entity-level tracking
                # Use scripted update to merge with existing processed_entities
                # AND set processed_to_dgraph to true to prevent reprocessing
                es.update(
                    index=ES_INDEX_NAME,
                    id=doc['_id'],
                    body={
                        "script": {
                            "source": """
                                if (ctx._source.processed_entities == null) {
                                    ctx._source.processed_entities = new HashMap();
                                }
                                for (entry in params.entities.entrySet()) {
                                    ctx._source.processed_entities[entry.getKey()] = entry.getValue();
                                }
                                ctx._source.last_dgraph_update = params.timestamp;
                                ctx._source.processed_to_dgraph = true;
                                ctx._source.dgraph_processed_at = params.timestamp;
                            """,
                            "params": {
                                "entities": {et: True for et in entity_types},
                                "timestamp": timestamp
                            }
                        }
                    }
                )
            else:
                # Legacy mode: mark entire document as processed
                es.update(
                    index=ES_INDEX_NAME,
                    id=doc['_id'],
                    body={
                        "doc": {
                            "processed_to_dgraph": True,
                            "dgraph_processed_at": timestamp
                        }
                    }
                )
        
        logger.info(f"Marked {len(documents)} documents as processed" + 
                   (f" for entities: {entity_types}" if entity_types else ""))
        return True
    except Exception as e:
        logger.error(f"Error marking documents as processed: {e}")
        return False


def mark_documents_with_per_doc_entities(es: Elasticsearch, doc_entities: Dict[str, List[str]]) -> bool:
    """
    Mark documents as processed with per-document entity tracking
    Each document is marked with only the entities it actually contains
    
    Args:
        es: Elasticsearch client
        doc_entities: Dictionary mapping document _id to list of entity types
                     Example: {"doc1": ["judgment", "citations"], "doc2": ["judgment", "court"]}
    
    Returns:
        True if successful, False otherwise
    """
    try:
        timestamp = datetime.utcnow().isoformat()
        
        for doc_id, entity_types in doc_entities.items():
            if not entity_types:
                logger.warning(f"No entities found for document {doc_id}, skipping")
                continue
            
            # Update with only the entities that exist in this specific document
            es.update(
                index=ES_INDEX_NAME,
                id=doc_id,
                body={
                    "script": {
                        "source": """
                            if (ctx._source.processed_entities == null) {
                                ctx._source.processed_entities = new HashMap();
                            }
                            for (entry in params.entities.entrySet()) {
                                ctx._source.processed_entities[entry.getKey()] = entry.getValue();
                            }
                            ctx._source.last_dgraph_update = params.timestamp;
                            ctx._source.processed_to_dgraph = true;
                            ctx._source.dgraph_processed_at = params.timestamp;
                        """,
                        "params": {
                            "entities": {et: True for et in entity_types},
                            "timestamp": timestamp
                        }
                    }
                }
            )
        
        logger.info(f"✅ Marked {len(doc_entities)} documents with per-document entity tracking")
        return True
    except Exception as e:
        logger.error(f"❌ Error marking documents with per-document entities: {e}")
        return False


def get_elasticsearch_stats(es: Elasticsearch) -> Dict:
    """Get statistics from Elasticsearch"""
    try:
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
            "total_documents": total_count,
            "processed_documents": processed_count,
            "unprocessed_documents": unprocessed_count
        }
    except Exception as e:
        logger.error(f"Error getting Elasticsearch stats: {e}")
        return {
            "total_documents": 0,
            "processed_documents": 0,
            "unprocessed_documents": 0,
            "error": str(e)
        }
