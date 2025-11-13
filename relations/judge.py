#!/usr/bin/env python3
"""
Judge Relation Handler
Handles: Judgment --[judged_by]--> Judge
"""

import hashlib
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class JudgeRelation:
    """
    Handles judge relationships with judgments
    Relationship: Judgment --[judged_by]--> Judge
    """
    
    def __init__(self):
        self.local_judges = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_judges = {}
    
    def extract_judges(self, source: Dict[str, Any]) -> List[str]:
        """
        Extract judges from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            List of judge names
        """
        judges = source.get('judges', [])
        
        # Ensure it's a list
        if not isinstance(judges, list):
            judges = [judges] if judges else []
        
        # Clean up
        judges = [j.strip() for j in judges if j and j.strip()]
        
        logger.debug(f"Extracted {len(judges)} judges")
        return judges
    
    def build_query_parts(self, judges: List[str]) -> Tuple[List[str], List[str]]:
        """
        Build query parts for judge lookups
        
        Args:
            judges: List of judge names
            
        Returns:
            Tuple of (query_parts, judge_vars)
        """
        query_parts = []
        judge_vars = []
        
        for judge in judges:
            if judge not in self.local_judges:
                judge_hash = self.get_hash(judge)
                self.local_judges[judge] = judge_hash
                escaped_judge = judge.replace('"', '\\"')
                var_name = f"judge_{judge_hash}"
                query_parts.append(f"{var_name} as var(func: eq(name, \"{escaped_judge}\")) @filter(type(Judge))")
            
            judge_hash = self.local_judges[judge]
            judge_vars.append(f"judge_{judge_hash}")
        
        logger.debug(f"Built {len(query_parts)} judge queries")
        return query_parts, judge_vars
    
    def build_judge_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all judge nodes
        
        Returns:
            List of judge node dictionaries
        """
        nodes = []
        
        for judge, judge_hash in self.local_judges.items():
            nodes.append({
                "uid": f"uid(judge_{judge_hash})",
                "judge_id": f"judge_{judge_hash}",
                "name": judge,
                "dgraph.type": "Judge"
            })
        
        logger.debug(f"Built {len(nodes)} judge nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed judges"""
        return {
            "total_judges": len(self.local_judges)
        }
