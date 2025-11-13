#!/usr/bin/env python3
"""
Judgment Relation Handler
Main node (Title) that connects to all other entities
"""

import hashlib
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class JudgmentRelation:
    """
    Handles the main Judgment node (Title)
    This is the central node that all other entities connect to
    """
    
    def __init__(self):
        self.processed_judgments = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def extract_judgment_data(self, doc: Dict, idx: int) -> Dict[str, Any]:
        """
        Extract judgment data from Elasticsearch document
        
        Args:
            doc: Elasticsearch document
            idx: Document index number
            
        Returns:
            Dictionary with judgment data
        """
        source = doc['_source']
        
        # Extract title (main identifier)
        title = source.get('title', '').strip()
        
        # Extract doc_id and remove 'doc_' prefix if present
        doc_id = source.get('doc_id', '').strip()
        if not doc_id:
            doc_id = doc['_id']
        if doc_id.startswith('doc_'):
            doc_id = doc_id[4:]  # Remove 'doc_' prefix
        
        # Extract other fields
        year = source.get('year', None)
        processed_timestamp = source.get('processed_timestamp', None)
        
        judgment_data = {
            'idx': idx,
            'title': title,
            'doc_id': doc_id,
            'year': year,
            'processed_timestamp': processed_timestamp,
            'judgment_id': f"J_{doc_id}",
            'escaped_title': title.replace('"', '\\"')
        }
        
        logger.debug(f"Extracted judgment: {judgment_data['title'][:50]}...")
        return judgment_data
    
    def build_query_part(self, judgment_data: Dict[str, Any]) -> str:
        """
        Build query part for judgment node lookup
        
        Args:
            judgment_data: Judgment data dictionary
            
        Returns:
            GraphQL query string
        """
        idx = judgment_data['idx']
        judgment_id = judgment_data['judgment_id']
        
        query = f"main_{idx} as var(func: eq(judgment_id, \"{judgment_id}\"))"
        return query
    
    def build_judgment_node(
        self,
        judgment_data: Dict[str, Any],
        citation_vars: List[str] = None,
        judge_vars: List[str] = None,
        petitioner_advocate_vars: List[str] = None,
        respondant_advocate_vars: List[str] = None,
        outcome_var: str = None,
        duration_var: str = None,
        court_var: str = None
    ) -> Dict[str, Any]:
        """
        Build the judgment node with all relationships
        
        Args:
            judgment_data: Judgment data dictionary
            citation_vars: List of citation variable names
            judge_vars: List of judge variable names
            petitioner_advocate_vars: List of petitioner advocate variable names
            respondant_advocate_vars: List of respondant advocate variable names
            outcome_var: Outcome variable name
            duration_var: Duration variable name
            court_var: Court variable name
            
        Returns:
            Judgment node dictionary
        """
        idx = judgment_data['idx']
        
        judgment_node = {
            "uid": f"uid(main_{idx})",
            "judgment_id": judgment_data['judgment_id'],
            "title": judgment_data['title'],
            "doc_id": judgment_data['doc_id'],
            "dgraph.type": "Judgment"
        }
        
        # Add optional fields
        if judgment_data.get('year') is not None:
            judgment_node["year"] = judgment_data['year']
        
        if judgment_data.get('processed_timestamp'):
            judgment_node["processed_timestamp"] = judgment_data['processed_timestamp']
        
        # Add relationships
        if citation_vars:
            judgment_node["cites"] = [{"uid": f"uid({var})"} for var in citation_vars]
        
        if judge_vars:
            judgment_node["judged_by"] = [{"uid": f"uid({var})"} for var in judge_vars]
        
        if petitioner_advocate_vars:
            judgment_node["petitioner_represented_by"] = [
                {"uid": f"uid({var})"} for var in petitioner_advocate_vars
            ]
        
        if respondant_advocate_vars:
            judgment_node["respondant_represented_by"] = [
                {"uid": f"uid({var})"} for var in respondant_advocate_vars
            ]
        
        if outcome_var:
            judgment_node["has_outcome"] = {"uid": f"uid({outcome_var})"}
        
        if duration_var:
            judgment_node["has_case_duration"] = {"uid": f"uid({duration_var})"}
        
        if court_var:
            judgment_node["court_heard_in"] = {"uid": f"uid({court_var})"}
        
        logger.debug(f"Built judgment node with {len([k for k in judgment_node.keys() if k not in ['uid', 'dgraph.type', 'judgment_id', 'title', 'doc_id', 'year', 'processed_timestamp']])} relationships")
        
        return judgment_node
