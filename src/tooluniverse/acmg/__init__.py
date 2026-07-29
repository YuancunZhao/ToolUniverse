"""ACMG evidence-only runtime.

The collector normalizes provider facts, applies five deterministic group rules,
and returns traceable EvidenceCards plus compatibility/Bayesian review. It does
not emit a five-tier classification.

EvidenceCards retain rule and SourceFact provenance. The guard blocks criterion
claims without corresponding validated EvidenceCards.
"""

from .models import EvidenceCard, SourceFact
from .population import population_evidence
from .computational import computational_evidence
from .clinical import clinical_evidence
from .functional import functional_evidence
from .literature import literature_evidence
from .guard import guard_acmg_answer
from .collector import ACMGEvidencePipeline

__all__ = [
    "EvidenceCard",
    "SourceFact",
    "ACMGEvidencePipeline",
    "clinical_evidence",
    "computational_evidence",
    "functional_evidence",
    "guard_acmg_answer",
    "literature_evidence",
    "population_evidence",
]
