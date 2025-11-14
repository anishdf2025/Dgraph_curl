#!/usr/bin/env python3
"""
Entity Detector
Detects which entities are present in Elasticsearch documents
Only marks entities as processed if they actually exist
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


def detect_entities_in_document(doc: Dict) -> List[str]:
    """
    Detect which entities are present in a document
    
    Args:
        doc: Elasticsearch document
        
    Returns:
        List of entity types that exist in the document
    """
    source = doc.get('_source', {})
    entities_found = []
    
    # Always include judgment (main node) - it has title
    if source.get('title'):
        entities_found.append('judgment')
    
    # Check for citations
    citations = source.get('citations', [])
    if citations and len(citations) > 0:
        entities_found.append('citations')
    
    # Check for judges
    judges = source.get('judges', [])
    if judges and len(judges) > 0:
        entities_found.append('judges')
    
    # Check for advocates (petitioner or respondant)
    petitioner_advocates = source.get('petitioner_advocates', [])
    respondant_advocates = source.get('respondant_advocates', [])
    if (petitioner_advocates and len(petitioner_advocates) > 0) or \
       (respondant_advocates and len(respondant_advocates) > 0):
        entities_found.append('advocates')
    
    # Check for outcome
    if source.get('outcome'):
        entities_found.append('outcome')
    
    # Check for case_duration
    if source.get('case_duration'):
        entities_found.append('case_duration')
    
    # Check for court
    if source.get('court'):
        entities_found.append('court')
    
    # Check for decision_date
    if source.get('decision_date'):
        entities_found.append('decision_date')
    
    # Check for filing_date
    if source.get('filing_date'):
        entities_found.append('filing_date')
    
    # Check for petitioner_party
    if source.get('petitioner_party'):
        entities_found.append('petitioner_party')
    
    # Check for respondant_party
    if source.get('respondant_party'):
        entities_found.append('respondant_party')
    
    # Check for case_number
    if source.get('case_number'):
        entities_found.append('case_number')
    
    # Check for summary
    if source.get('summary'):
        entities_found.append('summary')
    
    # Check for case_type
    if source.get('case_type'):
        entities_found.append('case_type')
    
    # Check for neutral_citation
    if source.get('neutral_citation'):
        entities_found.append('neutral_citation')
    
    # Check for acts
    acts = source.get('acts', [])
    if acts and len(acts) > 0:
        entities_found.append('acts')
    
    logger.debug(f"Document {doc.get('_id')} has entities: {entities_found}")
    return entities_found


def detect_entities_in_batch(documents: List[Dict]) -> Dict[str, List[str]]:
    """
    Detect entities for each document in a batch
    
    Args:
        documents: List of Elasticsearch documents
        
    Returns:
        Dictionary mapping document _id to list of entity types
    """
    doc_entities = {}
    
    for doc in documents:
        doc_id = doc.get('_id')
        entities = detect_entities_in_document(doc)
        doc_entities[doc_id] = entities
        
    logger.info(f"Detected entities for {len(documents)} documents")
    return doc_entities


def get_all_entities_from_batch(doc_entities: Dict[str, List[str]]) -> Set[str]:
    """
    Get all unique entities from a batch
    
    Args:
        doc_entities: Dictionary mapping document _id to list of entity types
        
    Returns:
        Set of all unique entity types in the batch
    """
    all_entities = set()
    for entities in doc_entities.values():
        all_entities.update(entities)
    
    return all_entities
