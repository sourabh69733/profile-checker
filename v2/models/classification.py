"""
Classification Pydantic Models

Models for resume classification results including:
- Experience level (FRESHER/EXPERIENCED)
- Tech domain detection
- Flags with reasons
- Scoring and confidence
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from typing import List, Literal, Optional, Any, ClassVar, Dict
from enum import Enum


# ============== Enums ==============

class ExperienceLevel(str, Enum):
    """Experience level classification."""
    FRESHER = "FRESHER"
    EXPERIENCED = "EXPERIENCED"


class FlagSeverity(str, Enum):
    """Severity levels for flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagType(str, Enum):
    """Type of flag (positive, negative, neutral)."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ============== Classification Model ==============

class Classification(BaseModel):
    """Core classification data."""
    
    experience_level: ExperienceLevel = ExperienceLevel.FRESHER
    tech_domain: str = "Unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    @field_validator('experience_level', mode='before')
    @classmethod
    def validate_experience_level(cls, v):
        """Validate and normalize experience level."""
        if v is None:
            return ExperienceLevel.FRESHER
        
        if isinstance(v, ExperienceLevel):
            return v
        
        v_upper = str(v).upper().strip()
        
        if v_upper == "FRESHER":
            return ExperienceLevel.FRESHER
        if v_upper == "EXPERIENCED":
            return ExperienceLevel.EXPERIENCED
        
        # Default to FRESHER for unknown values
        return ExperienceLevel.FRESHER
    
    @field_validator('confidence', mode='before')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if v is None:
            return 0.5
        
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        
        try:
            return max(0.0, min(1.0, float(v)))
        except (ValueError, TypeError):
            return 0.5
    
    @field_validator('tech_domain', mode='before')
    @classmethod
    def validate_tech_domain(cls, v):
        """Clean tech domain string."""
        if v is None or not v:
            return "Unknown"
        return str(v).strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experience_level": self.experience_level.value,
            "tech_domain": self.tech_domain,
            "confidence": self.confidence,
        }


# ============== Scoring Model ==============

class Scoring(BaseModel):
    """Scoring breakdown for classification."""
    
    fresher_score: int = Field(ge=0, le=100, default=50)
    experienced_score: int = Field(ge=0, le=100, default=50)
    deciding_factors: List[str] = Field(default_factory=list)
    
    @field_validator('fresher_score', 'experienced_score', mode='before')
    @classmethod
    def validate_scores(cls, v):
        """Ensure scores are between 0 and 100."""
        if v is None:
            return 50
        
        if isinstance(v, (int, float)):
            return max(0, min(100, int(v)))
        
        try:
            return max(0, min(100, int(float(v))))
        except (ValueError, TypeError):
            return 50
    
    @field_validator('deciding_factors', mode='before')
    @classmethod
    def validate_deciding_factors(cls, v):
        """Ensure deciding_factors is a list of strings."""
        if v is None:
            return []
        
        if isinstance(v, list):
            return [str(f).strip() for f in v if f and str(f).strip()]
        
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        
        return []
    
    @computed_field
    @property
    def dominant_classification(self) -> str:
        """Determine dominant classification based on scores."""
        if self.experienced_score > self.fresher_score:
            return "EXPERIENCED"
        return "FRESHER"
    
    @computed_field
    @property
    def score_difference(self) -> int:
        """Difference between scores (indicates confidence)."""
        return abs(self.experienced_score - self.fresher_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fresher_score": self.fresher_score,
            "experienced_score": self.experienced_score,
            "deciding_factors": self.deciding_factors,
            "dominant_classification": self.dominant_classification,
            "score_difference": self.score_difference,
        }


# ============== Flag Detail Model ==============

class FlagDetail(BaseModel):
    """Individual flag with reason and severity."""
    
    # Class-level constants (not model fields)
    VALID_FLAGS: ClassVar[List[str]] = [
        "career_gap",
        "career_switch",
        "overqualified",
        "underqualified",
        "frequent_job_changes",
        "no_formal_education",
        "strong_projects",
        "certification_heavy",
        "internship_only",
        "leadership_experience",
        "startup_experience",
        "faang_experience",
        "remote_work",
        "freelancer",
        "recent_graduate",
        "skill_mismatch",
        "diverse_experience",
        "consistent_growth",
        "technical_depth",
        "management_track",
    ]
    
    POSITIVE_FLAGS: ClassVar[List[str]] = [
        "strong_projects",
        "certification_heavy",
        "leadership_experience",
        "faang_experience",
        "consistent_growth",
        "technical_depth",
        "diverse_experience",
    ]
    
    NEGATIVE_FLAGS: ClassVar[List[str]] = [
        "career_gap",
        "frequent_job_changes",
        "underqualified",
        "skill_mismatch",
        "no_formal_education",
    ]
    
    # Model fields
    flag: str
    reason: str = ""
    severity: FlagSeverity = FlagSeverity.MEDIUM
    
    @field_validator('flag', mode='before')
    @classmethod
    def validate_flag(cls, v):
        """Validate flag name."""
        if v is None:
            return "unknown"
        
        v_lower = str(v).lower().strip().replace(' ', '_').replace('-', '_')
        
        if v_lower in cls.VALID_FLAGS:
            return v_lower
        
        # Try to match partial
        for valid_flag in cls.VALID_FLAGS:
            if valid_flag in v_lower or v_lower in valid_flag:
                return valid_flag
        
        return "unknown"
    
    @field_validator('reason', mode='before')
    @classmethod
    def validate_reason(cls, v):
        """Clean reason string."""
        if v is None:
            return ""
        return str(v).strip()
    
    @field_validator('severity', mode='before')
    @classmethod
    def validate_severity(cls, v):
        """Validate severity."""
        if v is None:
            return FlagSeverity.MEDIUM
        
        if isinstance(v, FlagSeverity):
            return v
        
        v_lower = str(v).lower().strip()
        
        if v_lower == "low":
            return FlagSeverity.LOW
        if v_lower == "high":
            return FlagSeverity.HIGH
        
        return FlagSeverity.MEDIUM
    
    @property
    def is_positive(self) -> bool:
        """Check if this is a positive flag (green flag)."""
        return self.flag in self.POSITIVE_FLAGS
    
    @property
    def is_negative(self) -> bool:
        """Check if this is a negative flag (red flag)."""
        return self.flag in self.NEGATIVE_FLAGS
    
    @property
    def is_neutral(self) -> bool:
        """Check if this is a neutral/informational flag."""
        return not self.is_positive and not self.is_negative
    
    @property
    def flag_type(self) -> FlagType:
        """Get the type of flag."""
        if self.is_positive:
            return FlagType.POSITIVE
        if self.is_negative:
            return FlagType.NEGATIVE
        return FlagType.NEUTRAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "flag": self.flag,
            "reason": self.reason,
            "severity": self.severity.value,
            "type": self.flag_type.value,
            "is_positive": self.is_positive,
            "is_negative": self.is_negative,
        }


# ============== Domain Evidence Model ==============

class DomainEvidence(BaseModel):
    """Evidence supporting domain classification."""
    
    primary_signals: List[str] = Field(default_factory=list)
    conflicting_signals: List[str] = Field(default_factory=list)
    
    @field_validator('primary_signals', 'conflicting_signals', mode='before')
    @classmethod
    def validate_signals(cls, v):
        """Ensure signals are lists of strings."""
        if v is None:
            return []
        
        if isinstance(v, list):
            return [str(s).strip() for s in v if s and str(s).strip()]
        
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        
        return []
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there are conflicting signals."""
        return len(self.conflicting_signals) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_signals": self.primary_signals,
            "conflicting_signals": self.conflicting_signals,
            "has_conflicts": self.has_conflicts,
        }


# ============== Main Classification Result Model ==============

class ClassificationResult(BaseModel):
    """
    Complete resume classification result.
    
    Contains:
    - Classification (experience level, tech domain, confidence)
    - Scoring (fresher/experienced scores, deciding factors)
    - Flags (with reasons and severity)
    - Domain evidence (signals supporting classification)
    - Summary (one-sentence verdict)
    """
    
    classification: Classification = Field(default_factory=Classification)
    scoring: Scoring = Field(default_factory=Scoring)
    flags: List[FlagDetail] = Field(default_factory=list)
    domain_evidence: DomainEvidence = Field(default_factory=DomainEvidence)
    summary: str = ""
    
    @field_validator('classification', mode='before')
    @classmethod
    def validate_classification(cls, v):
        """Parse classification."""
        if v is None:
            return Classification()
        if isinstance(v, Classification):
            return v
        if isinstance(v, dict):
            return Classification(**v)
        return Classification()
    
    @field_validator('scoring', mode='before')
    @classmethod
    def validate_scoring(cls, v):
        """Parse scoring."""
        if v is None:
            return Scoring()
        if isinstance(v, Scoring):
            return v
        if isinstance(v, dict):
            return Scoring(**v)
        return Scoring()
    
    @field_validator('domain_evidence', mode='before')
    @classmethod
    def validate_domain_evidence(cls, v):
        """Parse domain evidence."""
        if v is None:
            return DomainEvidence()
        if isinstance(v, DomainEvidence):
            return v
        if isinstance(v, dict):
            return DomainEvidence(**v)
        return DomainEvidence()
    
    @field_validator('flags', mode='before')
    @classmethod
    def validate_flags(cls, v: Any) -> List[FlagDetail]:
        """Parse and validate flags."""
        if v is None:
            return []
        
        if isinstance(v, list):
            validated_flags = []
            
            for item in v:
                if isinstance(item, FlagDetail):
                    if item.flag != "unknown":
                        validated_flags.append(item)
                
                elif isinstance(item, dict):
                    try:
                        flag_detail = FlagDetail(**item)
                        if flag_detail.flag != "unknown":
                            validated_flags.append(flag_detail)
                    except Exception:
                        pass
                
                elif isinstance(item, str):
                    # Handle plain string flags (backward compatibility)
                    if item.lower() in FlagDetail.VALID_FLAGS:
                        validated_flags.append(FlagDetail(
                            flag=item,
                            reason="No reason provided",
                            severity=FlagSeverity.MEDIUM
                        ))
            
            return validated_flags
        
        return []
    
    @field_validator('summary', mode='before')
    @classmethod
    def validate_summary(cls, v):
        """Clean summary string."""
        if v is None:
            return ""
        return str(v).strip()

    # ============== Computed Properties ==============

    @property
    def experience_level(self) -> ExperienceLevel:
        """Shortcut to get experience level."""
        return self.classification.experience_level
    
    @property
    def tech_domain(self) -> str:
        """Shortcut to get tech domain."""
        return self.classification.tech_domain
    
    @property
    def confidence(self) -> float:
        """Shortcut to get confidence."""
        return self.classification.confidence
    
    @property
    def is_fresher(self) -> bool:
        """Check if classified as fresher."""
        return self.classification.experience_level == ExperienceLevel.FRESHER
    
    @property
    def is_experienced(self) -> bool:
        """Check if classified as experienced."""
        return self.classification.experience_level == ExperienceLevel.EXPERIENCED
    
    @property
    def flag_names(self) -> List[str]:
        """Get list of flag names only."""
        return [f.flag for f in self.flags]
    
    @property
    def positive_flags(self) -> List[FlagDetail]:
        """Get all positive/green flags."""
        return [f for f in self.flags if f.is_positive]
    
    @property
    def negative_flags(self) -> List[FlagDetail]:
        """Get all negative/red flags."""
        return [f for f in self.flags if f.is_negative]
    
    @property
    def neutral_flags(self) -> List[FlagDetail]:
        """Get all neutral/informational flags."""
        return [f for f in self.flags if f.is_neutral]
    
    @property
    def high_severity_flags(self) -> List[FlagDetail]:
        """Get all high severity flags."""
        return [f for f in self.flags if f.severity == FlagSeverity.HIGH]
    
    @property
    def has_red_flags(self) -> bool:
        """Check if there are any red flags."""
        return len(self.negative_flags) > 0
    
    @property
    def has_green_flags(self) -> bool:
        """Check if there are any green flags."""
        return len(self.positive_flags) > 0
    
    @property
    def has_high_severity_issues(self) -> bool:
        """Check if there are high severity flags."""
        return len(self.high_severity_flags) > 0
    
    @property
    def risk_score(self) -> int:
        """
        Calculate risk score (0-100) based on negative flags.
        Higher score = higher risk.
        """
        score = 0
        
        for flag in self.negative_flags:
            if flag.severity == FlagSeverity.HIGH:
                score += 25
            elif flag.severity == FlagSeverity.MEDIUM:
                score += 15
            else:
                score += 5
        
        return min(score, 100)
    
    @property
    def strength_score(self) -> int:
        """
        Calculate strength score (0-100) based on positive flags.
        Higher score = stronger candidate.
        """
        score = 0
        
        for flag in self.positive_flags:
            if flag.severity == FlagSeverity.HIGH:
                score += 25
            elif flag.severity == FlagSeverity.MEDIUM:
                score += 15
            else:
                score += 10
        
        return min(score, 100)

    # ============== Helper Methods ==============

    def get_flag(self, flag_name: str) -> Optional[FlagDetail]:
        """Get a specific flag by name."""
        flag_name = flag_name.lower().strip()
        for f in self.flags:
            if f.flag == flag_name:
                return f
        return None
    
    def has_flag(self, flag_name: str) -> bool:
        """Check if a specific flag exists."""
        return flag_name.lower() in self.flag_names
    
    def get_flags_by_type(self, flag_type: FlagType) -> List[FlagDetail]:
        """Get flags by type (POSITIVE, NEGATIVE, NEUTRAL)."""
        if flag_type == FlagType.POSITIVE:
            return self.positive_flags
        if flag_type == FlagType.NEGATIVE:
            return self.negative_flags
        return self.neutral_flags
    
    def get_flags_by_severity(self, severity: FlagSeverity) -> List[FlagDetail]:
        """Get flags by severity."""
        return [f for f in self.flags if f.severity == severity]
    
    def get_flags_summary(self) -> Dict[str, Any]:
        """Get a summary of all flags with reasons."""
        return {
            "positive": [
                {"flag": f.flag, "reason": f.reason, "severity": f.severity.value}
                for f in self.positive_flags
            ],
            "negative": [
                {"flag": f.flag, "reason": f.reason, "severity": f.severity.value}
                for f in self.negative_flags
            ],
            "neutral": [
                {"flag": f.flag, "reason": f.reason, "severity": f.severity.value}
                for f in self.neutral_flags
            ],
            "risk_score": self.risk_score,
            "strength_score": self.strength_score,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "classification": self.classification.to_dict(),
            "scoring": self.scoring.to_dict(),
            "flags": [f.to_dict() for f in self.flags],
            "domain_evidence": self.domain_evidence.to_dict(),
            "summary": self.summary,
            "risk_score": self.risk_score,
            "strength_score": self.strength_score,
            "is_fresher": self.is_fresher,
            "is_experienced": self.is_experienced,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=indent)


# ============== Backward Compatibility Alias ==============

# If code was using ResumeClassification, this alias helps with migration
ResumeClassification = ClassificationResult