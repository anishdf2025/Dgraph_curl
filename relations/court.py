#!/usr/bin/env python3
"""
Court Relation Handler
Handles: Judgment --[court_heard_in]--> Court
"""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class CourtRelation:
    """
    Handles court relationships with judgments
    Relationship: Judgment --[court_heard_in]--> Court
    """
    
    def __init__(self):
        self.local_courts = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_courts = {}
    
    def extract_court(self, source: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract court information from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            Tuple of (court_name, court_location, court_bench)
        """
        court_name = source.get('court', '').strip()
        court_location = source.get('court_location', '').strip()
        court_bench = source.get('court_bench', '').strip()
        
        if court_name:
            logger.debug(f"Extracted court: {court_name}" + 
                        (f" ({court_location})" if court_location else "") +
                        (f" - {court_bench}" if court_bench else ""))
        
        return (court_name if court_name else None, 
                court_location if court_location else None,
                court_bench if court_bench else None)
    
    def build_query_parts(self, court_name: str, court_location: Optional[str], court_bench: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
        """
        Build query parts for court lookup
        
        Args:
            court_name: Court name
            court_location: Court location (optional)
            court_bench: Court bench type (optional)
            
        Returns:
            Tuple of (query_parts, court_var)
        """
        if not court_name:
            return [], None
        
        query_parts = []
        court_var = None
        
        # Create unique key for court (name + location)
        court_key = f"{court_name}_{court_location}" if court_location else court_name
        
        if court_key not in self.local_courts:
            court_hash = self.get_hash(court_key)
            self.local_courts[court_key] = {
                'hash': court_hash,
                'name': court_name,
                'location': court_location,
                'bench_type': court_bench
            }
            escaped_court = court_name.replace('"', '\\"')
            court_var = f"court_{court_hash}"
            
            if court_location:
                escaped_location = court_location.replace('"', '\\"')
                query_parts.append(
                    f"{court_var} as var(func: eq(name, \"{escaped_court}\")) "
                    f"@filter(type(Court) AND eq(location, \"{escaped_location}\"))"
                )
            else:
                query_parts.append(f"{court_var} as var(func: eq(name, \"{escaped_court}\")) @filter(type(Court))")
        else:
            court_hash = self.local_courts[court_key]['hash']
            court_var = f"court_{court_hash}"
        
        logger.debug(f"Built court query")
        return query_parts, court_var
    
    def build_court_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all court nodes
        
        Returns:
            List of court node dictionaries
        """
        nodes = []
        
        for court_key, court_data in self.local_courts.items():
            court_hash = court_data['hash']
            court_node = {
                "uid": f"uid(court_{court_hash})",
                "court_id": f"court_{court_hash}",
                "name": court_data['name'],
                "dgraph.type": "Court"
            }
            if court_data['location']:
                court_node["location"] = court_data['location']
            if court_data.get('bench_type'):
                court_node["bench_type"] = court_data['bench_type']
            nodes.append(court_node)
        
        logger.debug(f"Built {len(nodes)} court nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed courts"""
        return {
            "total_courts": len(self.local_courts)
        }
