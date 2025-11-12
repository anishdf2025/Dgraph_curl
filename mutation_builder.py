#!/usr/bin/env python3
"""
Mutation Builder
Orchestrates all relation handlers to build complete Dgraph mutations
"""

from typing import Dict, List, Any
import logging
from relations import (
    JudgmentRelation,
    CitationRelation,
    JudgeRelation,
    AdvocateRelation,
    OutcomeRelation,
    CaseDurationRelation,
    CourtRelation
)

logger = logging.getLogger(__name__)


class MutationBuilder:
    """
    Builds Dgraph mutations using modular relation handlers
    Each relation is handled by a separate class for better organization and debugging
    """
    
    def __init__(self):
        # Initialize all relation handlers
        self.judgment_handler = JudgmentRelation()
        self.citation_handler = CitationRelation()
        self.judge_handler = JudgeRelation()
        self.advocate_handler = AdvocateRelation()
        self.outcome_handler = OutcomeRelation()
        self.case_duration_handler = CaseDurationRelation()
        self.court_handler = CourtRelation()
        
        logger.info("✅ Mutation Builder initialized with all relation handlers")
    
    def build_mutation(self, documents: List[Dict]) -> Dict[str, Any]:
        """
        Build complete Dgraph mutation from Elasticsearch documents
        
        Args:
            documents: List of Elasticsearch documents
            
        Returns:
            Complete mutation dictionary with query and set blocks
        """
        logger.info(f"Building mutation for {len(documents)} documents...")
        
        # Reset all handlers for new batch
        self.citation_handler.reset()
        self.judge_handler.reset()
        self.advocate_handler.reset()
        self.outcome_handler.reset()
        self.case_duration_handler.reset()
        self.court_handler.reset()
        
        all_query_parts = []
        all_set_nodes = []
        
        # Process each document
        for idx, doc in enumerate(documents, 1):
            source = doc['_source']
            
            # 1. Extract judgment (main node) data
            judgment_data = self.judgment_handler.extract_judgment_data(doc, idx)
            judgment_query = self.judgment_handler.build_query_part(judgment_data)
            all_query_parts.append(judgment_query)
            
            # 2. Process Citations (Judgment -> Judgment)
            citations = self.citation_handler.extract_citations(source)
            citation_queries, citation_vars = self.citation_handler.build_query_parts(citations)
            all_query_parts.extend(citation_queries)
            
            # 3. Process Judges (Judgment -> Judge)
            judges = self.judge_handler.extract_judges(source)
            judge_queries, judge_vars = self.judge_handler.build_query_parts(judges)
            all_query_parts.extend(judge_queries)
            
            # 4. Process Advocates (Judgment -> Advocate)
            petitioner_advocates, respondant_advocates = self.advocate_handler.extract_advocates(source)
            advocate_queries, petitioner_advocate_vars, respondant_advocate_vars = self.advocate_handler.build_query_parts(
                petitioner_advocates, respondant_advocates
            )
            all_query_parts.extend(advocate_queries)
            
            # 5. Process Outcome (Judgment -> Outcome)
            outcome = self.outcome_handler.extract_outcome(source)
            outcome_queries, outcome_var = self.outcome_handler.build_query_parts(outcome)
            all_query_parts.extend(outcome_queries)
            
            # 6. Process Case Duration (Judgment -> CaseDuration)
            case_duration = self.case_duration_handler.extract_case_duration(source)
            duration_queries, duration_var = self.case_duration_handler.build_query_parts(case_duration)
            all_query_parts.extend(duration_queries)
            
            # 7. Process Court (Judgment -> Court)
            court_name, court_location, court_bench = self.court_handler.extract_court(source)
            court_queries, court_var = self.court_handler.build_query_parts(court_name, court_location, court_bench)
            all_query_parts.extend(court_queries)
            
            # 8. Build complete judgment node with all relationships
            judgment_node = self.judgment_handler.build_judgment_node(
                judgment_data,
                citation_vars=citation_vars if citation_vars else None,
                judge_vars=judge_vars if judge_vars else None,
                petitioner_advocate_vars=petitioner_advocate_vars if petitioner_advocate_vars else None,
                respondant_advocate_vars=respondant_advocate_vars if respondant_advocate_vars else None,
                outcome_var=outcome_var,
                duration_var=duration_var,
                court_var=court_var
            )
            all_set_nodes.append(judgment_node)
        
        # Build all entity nodes
        all_set_nodes.extend(self.citation_handler.build_citation_nodes())
        all_set_nodes.extend(self.judge_handler.build_judge_nodes())
        all_set_nodes.extend(self.advocate_handler.build_advocate_nodes())
        all_set_nodes.extend(self.outcome_handler.build_outcome_nodes())
        all_set_nodes.extend(self.case_duration_handler.build_case_duration_nodes())
        all_set_nodes.extend(self.court_handler.build_court_nodes())
        
        # Create final mutation
        final_mutation = {
            "query": "{\n  " + "\n  ".join(all_query_parts) + "\n}",
            "set": all_set_nodes
        }
        
        # Log statistics
        stats = self.get_stats()
        logger.info(f"✅ Mutation built successfully:")
        logger.info(f"   📚 Citations: {stats['citations']}")
        logger.info(f"   👨‍⚖️  Judges: {stats['judges']}")
        logger.info(f"   👔 Advocates: {stats['advocates']}")
        logger.info(f"   🎯 Outcomes: {stats['outcomes']}")
        logger.info(f"   ⏱️  Case Durations: {stats['case_durations']}")
        logger.info(f"   🏛️  Courts: {stats['courts']}")
        logger.info(f"   🔢 Total nodes: {len(all_set_nodes)}")
        
        return final_mutation
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics from all relation handlers
        
        Returns:
            Dictionary with statistics from each handler
        """
        return {
            "citations": self.citation_handler.get_stats()['total_citations'],
            "judges": self.judge_handler.get_stats()['total_judges'],
            "advocates": self.advocate_handler.get_stats()['total_advocates'],
            "outcomes": self.outcome_handler.get_stats()['total_outcomes'],
            "case_durations": self.case_duration_handler.get_stats()['total_case_durations'],
            "courts": self.court_handler.get_stats()['total_courts']
        }


# === Convenience function for backward compatibility ===
def build_dgraph_mutation(documents: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function to build mutation using MutationBuilder class
    
    Args:
        documents: List of Elasticsearch documents
        
    Returns:
        Complete mutation dictionary
    """
    builder = MutationBuilder()
    return builder.build_mutation(documents)
