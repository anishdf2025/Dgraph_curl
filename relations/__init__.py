"""
Relations Module
Each file handles a specific entity and its relationship with Judgment (title)
"""

from .judgment import JudgmentRelation
from .citation import CitationRelation
from .judge import JudgeRelation
from .advocate import AdvocateRelation
from .outcome import OutcomeRelation
from .case_duration import CaseDurationRelation
from .court import CourtRelation

__all__ = [
    'JudgmentRelation',
    'CitationRelation',
    'JudgeRelation',
    'AdvocateRelation',
    'OutcomeRelation',
    'CaseDurationRelation',
    'CourtRelation'
]
