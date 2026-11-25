"""Clinical Escalation & OPEL Copilot Package for AE-Watch UK (v2).

Author: CHRISH PEP FELIX A
"""

from src.agents.clinical_copilot import (
    ClinicalCorpusRetriever,
    ClinicalEscalationCopilot,
    calculate_opel_tier,
    clinical_copilot,
    load_nhs_clinical_corpus,
)

__all__ = [
    "ClinicalCorpusRetriever",
    "ClinicalEscalationCopilot",
    "calculate_opel_tier",
    "clinical_copilot",
    "load_nhs_clinical_corpus",
]
