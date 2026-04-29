from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Any, ClassVar
from enum import Enum

# ============== Enums ==============

class ExperienceLevel(str, Enum):
    """Experience level classification"""
    FRESHER = "FRESHER"
    EXPERIENCED = "EXPERIENCED"


class FlagSeverity(str, Enum):
    """Severity levels for flags"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagType(str, Enum):
    """Type of flag"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ============== Models ==============

class Classification(BaseModel):
    """Core classification data"""
    experience_level: ExperienceLevel = ExperienceLevel.FRESHER
    tech_domain: str = "Unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    @field_validator('confidence', mode='before')
    @classmethod
    def validate_confidence(cls, v):
        if v is None:
            return 0.5
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return 0.5
    
    @field_validator('experience_level', mode='before')
    @classmethod
    def validate_experience_level(cls, v):
        if v is None:
            return ExperienceLevel.FRESHER
        if isinstance(v, ExperienceLevel):
            return v
        v_upper = str(v).upper().strip()
        if v_upper == "FRESHER":
            return ExperienceLevel.FRESHER
        if v_upper == "EXPERIENCED":
            return ExperienceLevel.EXPERIENCED
        return ExperienceLevel.FRESHER


class Scoring(BaseModel):
    """Scoring breakdown for classification"""
    fresher_score: int = Field(ge=0, le=100, default=50)
    experienced_score: int = Field(ge=0, le=100, default=50)
    deciding_factors: List[str] = []
    
    @field_validator('fresher_score', 'experienced_score', mode='before')
    @classmethod
    def validate_scores(cls, v):
        if v is None:
            return 50
        if isinstance(v, (int, float)):
            return max(0, min(100, int(v)))
        return 50


class FlagDetail(BaseModel):
    """Individual flag with reason and severity"""
    
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
        "skill_mismatch"
    ]
    
    POSITIVE_FLAGS: ClassVar[List[str]] = [
        "strong_projects", 
        "certification_heavy", 
        "leadership_experience",
        "faang_experience"
    ]
    
    NEGATIVE_FLAGS: ClassVar[List[str]] = [
        "career_gap",
        "frequent_job_changes",
        "underqualified",
        "skill_mismatch"
    ]
    
    # Model fields
    flag: str
    reason: str = ""
    severity: FlagSeverity = FlagSeverity.MEDIUM
    
    @field_validator('flag', mode='before')
    @classmethod
    def validate_flag(cls, v):
        if v is None:
            return "unknown"
        v_lower = str(v).lower().strip()
        if v_lower in cls.VALID_FLAGS:
            return v_lower
        return "unknown"
    
    @field_validator('severity', mode='before')
    @classmethod
    def validate_severity(cls, v):
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
        """Check if this is a positive flag (green flag)"""
        return self.flag in self.POSITIVE_FLAGS
    
    @property
    def is_negative(self) -> bool:
        """Check if this is a negative flag (red flag)"""
        return self.flag in self.NEGATIVE_FLAGS
    
    @property
    def is_neutral(self) -> bool:
        """Check if this is a neutral/informational flag"""
        return not self.is_positive and not self.is_negative
    
    @property
    def flag_type(self) -> FlagType:
        """Get the type of flag"""
        if self.is_positive:
            return FlagType.POSITIVE
        if self.is_negative:
            return FlagType.NEGATIVE
        return FlagType.NEUTRAL


class DomainEvidence(BaseModel):
    """Evidence supporting domain classification"""
    primary_signals: List[str] = []
    conflicting_signals: List[str] = []


class ClassificationResult(BaseModel):
    """Complete resume classification result"""
    
    classification: Classification = Classification()
    scoring: Scoring = Scoring()
    flags: List[FlagDetail] = []
    domain_evidence: DomainEvidence = DomainEvidence()
    summary: str = ""
    
    @field_validator('flags', mode='before')
    @classmethod
    def validate_flags(cls, v: Any) -> List[FlagDetail]:
        if v is None:
            return []
        
        if isinstance(v, list):
            validated_flags = []
            for item in v:
                if isinstance(item, FlagDetail):
                    validated_flags.append(item)
                elif isinstance(item, dict):
                    try:
                        flag_detail = FlagDetail(**item)
                        if flag_detail.flag != "unknown":
                            validated_flags.append(flag_detail)
                    except Exception:
                        pass
                elif isinstance(item, str):
                    # Backward compatibility: handle plain string flags
                    if item in FlagDetail.VALID_FLAGS:
                        validated_flags.append(FlagDetail(
                            flag=item,
                            reason="No reason provided",
                            severity=FlagSeverity.MEDIUM
                        ))
            return validated_flags
        
        return []
    
    @field_validator('classification', mode='before')
    @classmethod
    def validate_classification(cls, v):
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
        if v is None:
            return DomainEvidence()
        if isinstance(v, DomainEvidence):
            return v
        if isinstance(v, dict):
            return DomainEvidence(**v)
        return DomainEvidence()
    
    # ============== Computed Properties ==============
    
    @property
    def experience_level(self) -> ExperienceLevel:
        """Shortcut to get experience level"""
        return self.classification.experience_level
    
    @property
    def is_fresher(self) -> bool:
        return self.classification.experience_level == ExperienceLevel.FRESHER
    
    @property
    def is_experienced(self) -> bool:
        return self.classification.experience_level == ExperienceLevel.EXPERIENCED
    
    @property
    def flag_names(self) -> List[str]:
        """Get list of flag names only (for quick checks)"""
        return [f.flag for f in self.flags]
    
    @property
    def positive_flags(self) -> List[FlagDetail]:
        """Get all positive/green flags"""
        return [f for f in self.flags if f.is_positive]
    
    @property
    def negative_flags(self) -> List[FlagDetail]:
        """Get all negative/red flags"""
        return [f for f in self.flags if f.is_negative]
    
    @property
    def neutral_flags(self) -> List[FlagDetail]:
        """Get all neutral/informational flags"""
        return [f for f in self.flags if f.is_neutral]
    
    @property
    def high_severity_flags(self) -> List[FlagDetail]:
        """Get all high severity flags"""
        return [f for f in self.flags if f.severity == FlagSeverity.HIGH]
    
    @property
    def has_red_flags(self) -> bool:
        return len(self.negative_flags) > 0
    
    @property
    def has_green_flags(self) -> bool:
        return len(self.positive_flags) > 0
    
    @property
    def has_high_severity_issues(self) -> bool:
        return len(self.high_severity_flags) > 0
    
    @property
    def risk_score(self) -> int:
        """
        Calculate risk score (0-100) based on negative flags and severity.
        Higher score = higher risk
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
    
    # ============== Helper Methods ==============
    
    def get_flag(self, flag_name: str) -> Optional[FlagDetail]:
        """Get a specific flag by name"""
        for f in self.flags:
            if f.flag == flag_name:
                return f
        return None
    
    def has_flag(self, flag_name: str) -> bool:
        """Check if a specific flag exists"""
        return flag_name in self.flag_names
    
    def get_flags_summary(self) -> dict:
        """Get a summary of all flags with reasons"""
        return {
            "positive": [{"flag": f.flag, "reason": f.reason} for f in self.positive_flags],
            "negative": [{"flag": f.flag, "reason": f.reason, "severity": f.severity.value} for f in self.negative_flags],
            "neutral": [{"flag": f.flag, "reason": f.reason} for f in self.neutral_flags],
            "risk_score": self.risk_score
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "classification": {
                "experience_level": self.classification.experience_level.value,
                "tech_domain": self.classification.tech_domain,
                "confidence": self.classification.confidence
            },
            "scoring": {
                "fresher_score": self.scoring.fresher_score,
                "experienced_score": self.scoring.experienced_score,
                "deciding_factors": self.scoring.deciding_factors
            },
            "flags": [
                {
                    "flag": f.flag,
                    "reason": f.reason,
                    "severity": f.severity.value,
                    "type": f.flag_type.value
                }
                for f in self.flags
            ],
            "domain_evidence": {
                "primary_signals": self.domain_evidence.primary_signals,
                "conflicting_signals": self.domain_evidence.conflicting_signals
            },
            "summary": self.summary,
            "risk_score": self.risk_score
        }


# ============== Backward Compatibility Alias ==============
# If you were using ResumeClassification elsewhere, this alias helps
ResumeClassification = ClassificationResult