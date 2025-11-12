#!/usr/bin/env python3
"""
Case Duration Relation Handler
Handles: Judgment --[has_case_duration]--> CaseDuration
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class CaseDurationRelation:
    """
    Handles case duration relationships with judgments
    Relationship: Judgment --[has_case_duration]--> CaseDuration
    """
    
    def __init__(self):
        self.local_case_durations = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_case_durations = {}
    
    def extract_case_duration(self, source: Dict[str, Any]) -> Optional[str]:
        """
        Extract case duration from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            Case duration string or None
        """
        case_duration = source.get('case_duration', '').strip()
        
        if case_duration:
            logger.debug(f"Extracted case duration: {case_duration}")
        
        return case_duration if case_duration else None
    
    def build_query_parts(self, case_duration: str) -> Tuple[List[str], Optional[str]]:
        """
        Build query parts for case duration lookup
        
        Args:
            case_duration: Case duration string
            
        Returns:
            Tuple of (query_parts, duration_var)
        """
        if not case_duration:
            return [], None
        
        query_parts = []
        duration_var = None
        
        if case_duration not in self.local_case_durations:
            duration_hash = self.get_hash(case_duration)
            self.local_case_durations[case_duration] = duration_hash
            escaped_duration = case_duration.replace('"', '\\"')
            duration_var = f"duration_{duration_hash}"
            query_parts.append(f"{duration_var} as var(func: eq(duration, \"{escaped_duration}\")) @filter(type(CaseDuration))")
        else:
            duration_hash = self.local_case_durations[case_duration]
            duration_var = f"duration_{duration_hash}"
        
        logger.debug(f"Built case duration query")
        return query_parts, duration_var
    
    def build_case_duration_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all case duration nodes
        
        Returns:
            List of case duration node dictionaries
        """
        nodes = []
        
        for duration, duration_hash in self.local_case_durations.items():
            nodes.append({
                "uid": f"uid(duration_{duration_hash})",
                "case_duration_id": f"duration_{duration_hash}",
                "duration": duration,
                "dgraph.type": "CaseDuration"
            })
        
        logger.debug(f"Built {len(nodes)} case duration nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed case durations"""
        return {
            "total_case_durations": len(self.local_case_durations)
        }
