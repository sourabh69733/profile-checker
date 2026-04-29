"""
Models Package

Contains Pydantic models for resume parsing and classification.
"""

from models.resume import (
    Resume,
    Experience,
    Education,
    Certification,
    Project,
    Gap,
    ExperienceMetrics,
    ParsingNotes,
)

from models.classification import (
    ClassificationResult,
    Classification,
    Scoring,
    DomainEvidence,
    FlagDetail,
    ExperienceLevel,
    FlagSeverity,
    FlagType,
)

__all__ = [
    # Resume models
    "Resume",
    "Experience",
    "Education",
    "Certification",
    "Project",
    "Gap",
    "ExperienceMetrics",
    "ParsingNotes",
    # Classification models
    "ClassificationResult",
    "Classification",
    "Scoring",
    "DomainEvidence",
    "FlagDetail",
    "ExperienceLevel",
    "FlagSeverity",
    "FlagType",
]