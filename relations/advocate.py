#!/usr/bin/env python3
"""
Advocate Relation Handler
Handles:
  - Judgment --[petitioner_represented_by]--> Advocate
  - Judgment --[respondant_represented_by]--> Advocate
"""

import hashlib
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class AdvocateRelation:
    """
    Handles advocate relationships with judgments
    Relationships:
      - Judgment --[petitioner_represented_by]--> Advocate (petitioner)
      - Judgment --[respondant_represented_by]--> Advocate (respondant)
    """
    
    def __init__(self):
        self.local_advocates = {}
    
    @staticmethod
    def get_hash(text: str) -> str:
        """Generate a unique hash for any text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def reset(self):
        """Reset local tracking for new batch"""
        self.local_advocates = {}
    
    def extract_advocates(self, source: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Extract advocates from Elasticsearch document
        
        Args:
            source: Elasticsearch document _source
            
        Returns:
            Tuple of (petitioner_advocates, respondant_advocates)
        """
        petitioner_advocates = source.get('petitioner_advocates', [])
        respondant_advocates = source.get('respondant_advocates', [])
        
        # Ensure lists
        if not isinstance(petitioner_advocates, list):
            petitioner_advocates = [petitioner_advocates] if petitioner_advocates else []
        if not isinstance(respondant_advocates, list):
            respondant_advocates = [respondant_advocates] if respondant_advocates else []
        
        # Clean up
        petitioner_advocates = [a.strip() for a in petitioner_advocates if a and a.strip()]
        respondant_advocates = [a.strip() for a in respondant_advocates if a and a.strip()]
        
        logger.debug(f"Extracted {len(petitioner_advocates)} petitioner advocates, {len(respondant_advocates)} respondant advocates")
        return petitioner_advocates, respondant_advocates
    
    def build_query_parts(
        self,
        petitioner_advocates: List[str],
        respondant_advocates: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Build query parts for advocate lookups
        
        Args:
            petitioner_advocates: List of petitioner advocate names
            respondant_advocates: List of respondant advocate names
            
        Returns:
            Tuple of (query_parts, petitioner_advocate_vars, respondant_advocate_vars)
        """
        query_parts = []
        petitioner_advocate_vars = []
        respondant_advocate_vars = []
        
        # Track petitioner advocates
        for advocate in petitioner_advocates:
            if advocate not in self.local_advocates:
                advocate_hash = self.get_hash(advocate)
                self.local_advocates[advocate] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                query_parts.append(
                    f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) "
                    f"@filter(type(Advocate) AND eq(advocate_type, \"petitioner\"))"
                )
            
            advocate_hash = self.local_advocates[advocate]
            petitioner_advocate_vars.append(f"adv_{advocate_hash}")
        
        # Track respondant advocates
        for advocate in respondant_advocates:
            advocate_key = f"{advocate}_respondant"
            if advocate_key not in self.local_advocates:
                advocate_hash = self.get_hash(advocate_key)
                self.local_advocates[advocate_key] = advocate_hash
                escaped_advocate = advocate.replace('"', '\\"')
                var_name = f"adv_{advocate_hash}"
                query_parts.append(
                    f"{var_name} as var(func: eq(name, \"{escaped_advocate}\")) "
                    f"@filter(type(Advocate) AND eq(advocate_type, \"respondant\"))"
                )
            
            advocate_hash = self.local_advocates[advocate_key]
            respondant_advocate_vars.append(f"adv_{advocate_hash}")
        
        logger.debug(f"Built {len(query_parts)} advocate queries")
        return query_parts, petitioner_advocate_vars, respondant_advocate_vars
    
    def build_advocate_nodes(self) -> List[Dict[str, Any]]:
        """
        Build all advocate nodes
        
        Returns:
            List of advocate node dictionaries
        """
        nodes = []
        
        for advocate_key, advocate_hash in self.local_advocates.items():
            advocate_name = advocate_key.replace("_respondant", "")
            advocate_type = "respondant" if "_respondant" in advocate_key else "petitioner"
            
            nodes.append({
                "uid": f"uid(adv_{advocate_hash})",
                "advocate_id": f"adv_{advocate_hash}",
                "name": advocate_name,
                "advocate_type": advocate_type,
                "dgraph.type": "Advocate"
            })
        
        logger.debug(f"Built {len(nodes)} advocate nodes")
        return nodes
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about processed advocates"""
        return {
            "total_advocates": len(self.local_advocates)
        }
