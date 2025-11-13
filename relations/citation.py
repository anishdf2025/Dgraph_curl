#!/usr/bin/env python3
"""
Citation Relation Handler
Handles: Judgment --[cites]--> Judgment (other cases cited)
"""

import hashlib
import json
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class CitationRelation:
    """
    Handles citation relationships between judgments
    Relationship: Judgment --[cites]--> Judgment
    """
    
    def __init__(self):
        self.local_citations = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_citations = {}
    
    def extract_citations(self, source: Dict[str, Any]) -> List[str]:
        """
        Extract citations from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            List of citation strings
        """
        citations = source.get('citations', [])
        
        # Ensure it's a list
        if isinstance(citations, str):
            try:
                citations = json.loads(citations)
            except:
                citations = [citations] if citations else []
        elif not isinstance(citations, list):
            citations = []
        
        # Clean up
        citations = [c.strip() for c in citations if c and c.strip()]
        
        logger.debug(f"Extracted {len(citations)} citations")
        return citations
    
    def build_query_parts(self, citations: List[str]) -> Tuple[List[str], List[str]]:
        """
        Build query parts for citation lookups
        
        Args:
            citations: List of citation strings
            
        Returns:
            Tuple of (query_parts, citation_vars)
        """
        query_parts = []
        citation_vars = []
        
        for citation in citations:
            if citation not in self.local_citations:
                citation_hash = self.get_hash(citation)
                self.local_citations[citation] = citation_hash
                escaped_citation = citation.replace('"', '\\"')
                var_name = f"cite_{citation_hash}"
                query_parts.append(f"{var_name} as var(func: eq(title, \"{escaped_citation}\"))")
            
            citation_hash = self.local_citations[citation]
            citation_vars.append(f"cite_{citation_hash}")
        
        logger.debug(f"Built {len(query_parts)} citation queries")
        return query_parts, citation_vars
    
    def build_citation_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all citation nodes
        
        Returns:
            List of citation node dictionaries
        """
        nodes = []
        
        for citation, citation_hash in self.local_citations.items():
            nodes.append({
                "uid": f"uid(cite_{citation_hash})",
                "title": citation,
                "dgraph.type": "Judgment"
            })
        
        logger.debug(f"Built {len(nodes)} citation nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed citations"""
        return {
            "total_citations": len(self.local_citations)
        }
