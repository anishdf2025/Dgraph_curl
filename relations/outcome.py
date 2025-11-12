#!/usr/bin/env python3
"""
Outcome Relation Handler
Handles: Judgment --[has_outcome]--> Outcome
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class OutcomeRelation:
    """
    Handles outcome relationships with judgments
    Relationship: Judgment --[has_outcome]--> Outcome
    """
    
    def __init__(self):
        self.local_outcomes = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_outcomes = {}
    
    def extract_outcome(self, source: Dict[str, Any]) -> Optional[str]:
        """
        Extract outcome from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            Outcome string or None
        """
        outcome = source.get('outcome', '').strip()
        
        if outcome:
            logger.debug(f"Extracted outcome: {outcome}")
        
        return outcome if outcome else None
    
    def build_query_parts(self, outcome: str) -> Tuple[List[str], Optional[str]]:
        """
        Build query parts for outcome lookup
        
        Args:
            outcome: Outcome string
            
        Returns:
            Tuple of (query_parts, outcome_var)
        """
        if not outcome:
            return [], None
        
        query_parts = []
        outcome_var = None
        
        if outcome not in self.local_outcomes:
            outcome_hash = self.get_hash(outcome)
            self.local_outcomes[outcome] = outcome_hash
            escaped_outcome = outcome.replace('"', '\\"')
            outcome_var = f"outcome_{outcome_hash}"
            query_parts.append(f"{outcome_var} as var(func: eq(name, \"{escaped_outcome}\")) @filter(type(Outcome))")
        else:
            outcome_hash = self.local_outcomes[outcome]
            outcome_var = f"outcome_{outcome_hash}"
        
        logger.debug(f"Built outcome query")
        return query_parts, outcome_var
    
    def build_outcome_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all outcome nodes
        
        Returns:
            List of outcome node dictionaries
        """
        nodes = []
        
        for outcome, outcome_hash in self.local_outcomes.items():
            nodes.append({
                "uid": f"uid(outcome_{outcome_hash})",
                "outcome_id": f"outcome_{outcome_hash}",
                "name": outcome,
                "dgraph.type": "Outcome"
            })
        
        logger.debug(f"Built {len(nodes)} outcome nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed outcomes"""
        return {
            "total_outcomes": len(self.local_outcomes)
        }
