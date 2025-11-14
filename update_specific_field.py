#!/usr/bin/env python3
"""
Update Specific Field in Existing Entities

This script updates ONLY a specific field in existing Dgraph nodes
without reprocessing or recreating relationships.

Usage:
    python3 update_specific_field.py --field court_bench
    python3 update_specific_field.py --field court_bench --dry-run
"""

import argparse
import logging
import json
from elasticsearch import Elasticsearch
from typing import List, Dict, Optional
import sys
import requests
import hashlib

from config import ES_HOST, ES_INDEX_NAME, DGRAPH_HOST
from elasticsearch_client import mark_documents_processed

# Use DGRAPH_HOST from config
DGRAPH_URL = DGRAPH_HOST

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_hash(text: str) -> str:
    """Generate a unique hash for any text (same as court.py)"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]


def fetch_documents_with_field(es: Elasticsearch, field_name: str) -> List[Dict]:
    """
    Fetch documents that have a specific field but haven't updated it in Dgraph
    
    Args:
        es: Elasticsearch client
        field_name: The field name (e.g., 'court_bench')
    """
    try:
        query = {
            "bool": {
                "must": [
                    {"exists": {"field": field_name}}
                ],
                "should": [
                    {"bool": {"must_not": {"exists": {"field": f"processed_entities.{field_name}"}}}},
                    {"term": {f"processed_entities.{field_name}": False}}
                ],
                "minimum_should_match": 1
            }
        }
        
        response = es.search(
            index=ES_INDEX_NAME,
            query=query,
            size=100,
            scroll='2m'
        )
        
        scroll_id = response['_scroll_id']
        documents = response['hits']['hits']
        
        while len(response['hits']['hits']) > 0:
            response = es.scroll(scroll_id=scroll_id, scroll='2m')
            if len(response['hits']['hits']) == 0:
                break
            documents.extend(response['hits']['hits'])
        
        es.clear_scroll(scroll_id=scroll_id)
        
        logger.info(f"Found {len(documents)} documents with unprocessed '{field_name}' field")
        return documents
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return []


def build_court_bench_update(documents: List[Dict]) -> Dict:
    """
    Build mutation to update bench_type for existing Court nodes
    AND connect Judgments to Courts
    
    This updates Court.bench_type and creates Judgment → Court relationship
    """
    query_parts = []
    set_nodes = []
    courts_to_update = {}
    judgment_to_court = []  # Track which judgment connects to which court
    
    for idx, doc in enumerate(documents, 1):
        source = doc['_source']
        doc_id = doc.get('_id', f"doc_{idx}")
        
        # Extract judgment info
        title = source.get('title', '').strip()
        
        # Extract court info
        court_name = source.get('court', '').strip()
        court_location = source.get('court_location', '').strip()
        court_bench = source.get('court_bench', '').strip()
        
        if not court_name or not court_bench:
            continue
        
        # Create unique key for court
        court_key = f"{court_name}_{court_location}" if court_location else court_name
        
        if court_key not in courts_to_update:
            court_hash = get_hash(court_key)
            courts_to_update[court_key] = {
                'hash': court_hash,
                'name': court_name,
                'location': court_location,
                'bench_type': court_bench
            }
        
        # Track judgment to court mapping
        judgment_to_court.append({
            'doc_id': doc_id,
            'title': title,
            'court_var': f"court_{courts_to_update[court_key]['hash']}"
        })
    
    # Build queries to find existing Court and Judgment nodes
    for court_key, court_data in courts_to_update.items():
        court_hash = court_data['hash']
        court_var = f"court_{court_hash}"
        escaped_name = court_data['name'].replace('"', '\\"')
        
        if court_data['location']:
            escaped_location = court_data['location'].replace('"', '\\"')
            query_parts.append(
                f"{court_var} as var(func: eq(name, \"{escaped_name}\")) "
                f"@filter(type(Court) AND eq(location, \"{escaped_location}\"))"
            )
        else:
            query_parts.append(
                f"{court_var} as var(func: eq(name, \"{escaped_name}\")) @filter(type(Court))"
            )
    
    # Add judgment queries
    for idx, mapping in enumerate(judgment_to_court, 1):
        judgment_var = f"main_{idx}"
        judgment_id = f"J_{mapping['doc_id']}"
        query_parts.append(
            f"{judgment_var} as var(func: eq(judgment_id, \"{judgment_id}\"))"
        )
        mapping['judgment_var'] = judgment_var
    
    # Build set nodes
    # 1. Update Court nodes with bench_type AND ensure all Court fields exist
    for court_key, court_data in courts_to_update.items():
        court_hash = court_data['hash']
        court_var = f"court_{court_hash}"
        
        court_node = {
            "uid": f"uid({court_var})",
            "court_id": f"court_{court_hash}",
            "name": court_data['name'],
            "dgraph.type": "Court",
            "bench_type": court_data['bench_type']
        }
        
        if court_data['location']:
            court_node["location"] = court_data['location']
        
        set_nodes.append(court_node)
    
    # 2. Connect Judgments to Courts
    for mapping in judgment_to_court:
        set_nodes.append({
            "uid": f"uid({mapping['judgment_var']})",
            "court_heard_in": {
                "uid": f"uid({mapping['court_var']})"
            }
        })
    
    mutation = {
        "query": "{\n  " + "\n  ".join(query_parts) + "\n}",
        "set": set_nodes
    }
    
    logger.info(f"Built mutation to update {len(courts_to_update)} Court nodes with bench_type")
    logger.info(f"And connect {len(judgment_to_court)} Judgments to Courts")
    return mutation


def upload_mutation(mutation: Dict) -> bool:
    """Upload mutation to Dgraph"""
    try:
        response = requests.post(
            f"{DGRAPH_URL}/mutate?commitNow=true",
            json=mutation,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Dgraph update successful")
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            logger.error(f"❌ Dgraph update failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error uploading to Dgraph: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Update specific field in existing Dgraph entities'
    )
    parser.add_argument(
        '--field',
        required=True,
        choices=['court_bench'],
        help='Field to update'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without actually updating'
    )
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    logger.info("Connecting to Elasticsearch...")
    es = Elasticsearch([ES_HOST])
    
    if not es.ping():
        logger.error("❌ Failed to connect to Elasticsearch")
        sys.exit(1)
    
    logger.info("✅ Connected to Elasticsearch")
    
    # Process court_bench field
    if args.field == 'court_bench':
        documents = fetch_documents_with_field(es, 'court_bench')
        
        if not documents:
            logger.info("✅ No documents to process")
            sys.exit(0)
        
        if args.dry_run:
            logger.info(f"\n{'='*60}")
            logger.info("DRY RUN: Would update these documents:")
            logger.info(f"{'='*60}")
            
            courts_to_update = {}
            for doc in documents:
                source = doc['_source']
                court_name = source.get('court', 'N/A')
                court_location = source.get('court_location', 'N/A')
                court_bench = source.get('court_bench', 'N/A')
                title = source.get('title', 'N/A')
                
                court_key = f"{court_name} ({court_location})"
                if court_key not in courts_to_update:
                    courts_to_update[court_key] = []
                courts_to_update[court_key].append({
                    'title': title,
                    'bench': court_bench
                })
            
            logger.info(f"\n📍 Courts that would be updated:")
            for court_key, docs in courts_to_update.items():
                logger.info(f"\n  Court: {court_key}")
                logger.info(f"  New bench_type: {docs[0]['bench']}")
                logger.info(f"  Affects {len(docs)} judgment(s):")
                for d in docs[:5]:  # Show first 5
                    logger.info(f"    - {d['title']}")
                if len(docs) > 5:
                    logger.info(f"    ... and {len(docs) - 5} more")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Total: {len(courts_to_update)} Court nodes would be updated")
            logger.info(f"Total: {len(documents)} judgments affected")
            logger.info(f"{'='*60}\n")
            sys.exit(0)
        
        # Build mutation
        mutation = build_court_bench_update(documents)
        
        # Save mutation for debugging
        with open('dgraph_field_update.json', 'w') as f:
            json.dump(mutation, f, indent=2)
        logger.info("💾 Saved mutation to dgraph_field_update.json")
        
        # Upload to Dgraph
        if upload_mutation(mutation):
            # Count actual court nodes updated (first half of set nodes)
            num_courts = len([node for node in mutation['set'] if 'bench_type' in node])
            num_judgments = len([node for node in mutation['set'] if 'court_heard_in' in node])
            
            # Mark documents as processed for court_bench
            if mark_documents_processed(es, documents, ['court_bench']):
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ SUCCESS!")
                logger.info(f"{'='*60}")
                logger.info(f"Updated bench_type for {num_courts} Court node(s)")
                logger.info(f"Connected {num_judgments} Judgment(s) to their Courts")
                logger.info(f"Marked {len(documents)} document(s) as processed for court_bench")
                logger.info(f"{'='*60}\n")
            else:
                logger.warning("⚠️  Updated Dgraph but failed to mark documents in Elasticsearch")
        else:
            logger.error("❌ Failed to update Dgraph")
            sys.exit(1)


if __name__ == "__main__":
    main()
