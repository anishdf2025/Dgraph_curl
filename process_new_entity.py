#!/usr/bin/env python3
"""
Process New Entity Fields for Existing Documents

This script allows you to add new entity fields to documents that were already processed.
For example, adding 'court_bench' to existing Court nodes without reprocessing everything.

Usage:
    python3 process_new_entity.py --entity court_bench
    python3 process_new_entity.py --entity acts
    python3 process_new_entity.py --entity all  # Process all new fields
"""

import argparse
import logging
from elasticsearch import Elasticsearch
from typing import List, Dict
import sys

from config import ES_HOST, ES_INDEX_NAME
from dgraph_client import apply_dgraph_schema, upload_to_dgraph
from mutation_builder import MutationBuilder
from elasticsearch_client import mark_documents_processed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_documents_missing_entity(es: Elasticsearch, entity_field: str) -> List[Dict]:
    """
    Fetch documents that have data for an entity but haven't processed it yet
    
    Args:
        es: Elasticsearch client
        entity_field: The source field name (e.g., 'court_bench', 'acts')
    """
    try:
        # Query for documents that:
        # 1. Have the source field with data
        # 2. Don't have processed_entities.{entity_field} = true
        query = {
            "bool": {
                "must": [
                    {"exists": {"field": entity_field}}
                ],
                "should": [
                    {"bool": {"must_not": {"exists": {"field": f"processed_entities.{entity_field}"}}}},
                    {"term": {f"processed_entities.{entity_field}": False}}
                ],
                "minimum_should_match": 1
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
        
        logger.info(f"Found {len(documents)} documents with unprocessed '{entity_field}' field")
        return documents
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return []


def process_court_bench(documents: List[Dict]) -> bool:
    """Process only the court_bench field for documents"""
    if not documents:
        logger.info("No documents to process for court_bench")
        return True
    
    logger.info(f"Processing court_bench for {len(documents)} documents...")
    
    # Build mutation focusing only on Court entity with bench_type
    builder = MutationBuilder()
    mutation = builder.build_mutation(documents)
    
    # Apply schema and upload
    if not apply_dgraph_schema(retry=True):
        logger.error("Failed to apply Dgraph schema")
        return False
    
    if not upload_to_dgraph(mutation, retry=True):
        logger.error("Failed to upload to Dgraph")
        return False
    
    return True


def process_acts(documents: List[Dict]) -> bool:
    """Process only the acts field for documents"""
    if not documents:
        logger.info("No documents to process for acts")
        return True
    
    logger.info(f"Processing acts for {len(documents)} documents...")
    
    # Build mutation focusing only on Act entities
    builder = MutationBuilder()
    mutation = builder.build_mutation(documents)
    
    # Apply schema and upload
    if not apply_dgraph_schema(retry=True):
        logger.error("Failed to apply Dgraph schema")
        return False
    
    if not upload_to_dgraph(mutation, retry=True):
        logger.error("Failed to upload to Dgraph")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Process new entity fields for existing documents'
    )
    parser.add_argument(
        '--entity',
        required=True,
        choices=['court_bench', 'acts', 'all'],
        help='Entity field to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    logger.info("Connecting to Elasticsearch...")
    es = Elasticsearch([ES_HOST])
    
    if not es.ping():
        logger.error("❌ Failed to connect to Elasticsearch")
        sys.exit(1)
    
    logger.info("✅ Connected to Elasticsearch")
    
    # Process based on entity type
    if args.entity == 'court_bench':
        documents = fetch_documents_missing_entity(es, 'court_bench')
        
        if args.dry_run:
            logger.info(f"DRY RUN: Would process {len(documents)} documents")
            for doc in documents[:5]:  # Show first 5
                logger.info(f"  - {doc['_id']}: {doc['_source'].get('title', 'N/A')}")
            sys.exit(0)
        
        if process_court_bench(documents):
            # Mark only court_bench as processed
            if mark_documents_processed(es, documents, ['court_bench']):
                logger.info(f"✅ Successfully processed court_bench for {len(documents)} documents")
            else:
                logger.error("❌ Failed to mark documents")
        else:
            logger.error("❌ Failed to process court_bench")
            sys.exit(1)
    
    elif args.entity == 'acts':
        documents = fetch_documents_missing_entity(es, 'acts')
        
        if args.dry_run:
            logger.info(f"DRY RUN: Would process {len(documents)} documents")
            for doc in documents[:5]:  # Show first 5
                logger.info(f"  - {doc['_id']}: {doc['_source'].get('title', 'N/A')}")
            sys.exit(0)
        
        if process_acts(documents):
            # Mark only acts as processed
            if mark_documents_processed(es, documents, ['acts']):
                logger.info(f"✅ Successfully processed acts for {len(documents)} documents")
            else:
                logger.error("❌ Failed to mark documents")
        else:
            logger.error("❌ Failed to process acts")
            sys.exit(1)
    
    elif args.entity == 'all':
        logger.info("Processing all new entity fields...")
        
        # Process court_bench
        court_bench_docs = fetch_documents_missing_entity(es, 'court_bench')
        if court_bench_docs:
            if not args.dry_run:
                if process_court_bench(court_bench_docs):
                    mark_documents_processed(es, court_bench_docs, ['court_bench'])
                    logger.info(f"✅ Processed court_bench for {len(court_bench_docs)} documents")
        
        # Process acts
        acts_docs = fetch_documents_missing_entity(es, 'acts')
        if acts_docs:
            if not args.dry_run:
                if process_acts(acts_docs):
                    mark_documents_processed(es, acts_docs, ['acts'])
                    logger.info(f"✅ Processed acts for {len(acts_docs)} documents")
        
        if args.dry_run:
            logger.info(f"DRY RUN: Would process {len(court_bench_docs)} court_bench + {len(acts_docs)} acts documents")


if __name__ == "__main__":
    main()
