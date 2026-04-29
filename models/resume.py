# models/resume.py
from pydantic import BaseModel, field_validator, computed_field
from typing import Optional, Any, Literal
from datetime import datetime

# ============== Parsing Models ==============

# NEW: Experience Metrics Model 👇
class ExperienceMetrics(BaseModel):
    total_full_time_months: int = 0
    total_internship_months: int = 0
    total_contract_months: int = 0
    total_freelance_months: int = 0
    
    @computed_field
    @property
    def total_professional_months(self) -> int:
        """Total months excluding internships (for experience classification)"""
        return self.total_full_time_months + self.total_contract_months + self.total_freelance_months
    
    @computed_field
    @property
    def total_all_months(self) -> int:
        """Total months including internships (for confidence scoring)"""
        return (
            self.total_full_time_months + 
            self.total_internship_months + 
            self.total_contract_months + 
            self.total_freelance_months
        )


class Experience(BaseModel):
    company: str = ""
    title: str = ""
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    duration_months: int = 0  # NEW: Duration in months for calculations 👇
    responsibilities: list[str] = []
    type: Optional[Literal["full-time", "internship", "contract", "freelance", "unknown"]] = "unknown"
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        valid_types = ["full-time", "internship", "contract", "freelance", "unknown"]
        if v is None or v not in valid_types:
            return "unknown"
        return v
    
    @field_validator('duration_months', mode='before')
    @classmethod
    def validate_duration_months(cls, v):
        """Ensure duration_months is always a valid integer"""
        if v is None:
            return 0
        if isinstance(v, int):
            return max(0, v)  # No negative months
        if isinstance(v, str):
            try:
                return max(0, int(v))
            except:
                return 0
        return 0


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None
    
    @field_validator('graduation_year', mode='before')
    @classmethod
    def parse_graduation_year(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v)
            except:
                return None
        return None


class Certification(BaseModel):
    name: str = ""
    issuer: Optional[str] = None
    date: Optional[str] = None


class Project(BaseModel):
    name: str = ""
    description: Optional[str] = None
    technologies: list[str] = []
    tech_stack: list[str] = []  # Alias for classifier
    outcome: Optional[str] = None
    
    @field_validator('tech_stack', mode='before')
    @classmethod
    def merge_tech(cls, v, info):
        # Merge technologies into tech_stack
        if not v:
            return info.data.get('technologies', [])
        return v


class Gap(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    reason: Optional[str] = None


class Personal(BaseModel):
    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class Resume(BaseModel):
    # Personal Information
    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    
    # Professional Summary
    summary: Optional[str] = None
    
    # Core Sections
    skills: list[str] = []
    experience: list[Experience] = []
    education: list[Education] = []
    
    # NEW: Experience Metrics for Classification 👇
    experience_metrics: ExperienceMetrics = ExperienceMetrics()
    
    # Optional Sections
    certifications: list[Certification] = []
    projects: list[Project] = []
    languages: list[str] = []
    gaps: list[Gap] = []  # For classifier
    
    # Metadata
    raw_text: Optional[str] = None
    parse_confidence: Optional[float] = None
    parsed_at: Optional[datetime] = None

    # ============== NEW: Computed Properties for Classification 👇 ==============
    
    @computed_field
    @property
    def candidate_status(self) -> Literal["FRESHER", "EXPERIENCED"]:
        """Classify candidate based on full-time experience only"""
        # Use experience_metrics if available (from LLM)
        if self.experience_metrics.total_full_time_months >= 12:
            return "EXPERIENCED"
        
        # Fallback: Calculate from individual experiences if metrics not set
        calculated_months = sum(
            exp.duration_months 
            for exp in self.experience 
            if exp.type in ["full-time", "contract", "freelance"]
        )
        
        if calculated_months >= 12:
            return "EXPERIENCED"
        
        return "FRESHER"
    
    @computed_field
    @property
    def experience_confidence_score(self) -> float:
        """
        Calculate confidence score (0-100) based on all experience types.
        Freshers with internships get higher confidence than those without.
        """
        metrics = self.experience_metrics
        
        # Base score
        if self.candidate_status == "EXPERIENCED":
            base_score = 70.0
            # More experience = higher confidence (max +30)
            experience_bonus = min(metrics.total_professional_months / 12 * 10, 30)
        else:
            base_score = 40.0
            # Internships boost fresher confidence (max +30)
            internship_bonus = min(metrics.total_internship_months * 3, 30)
            experience_bonus = internship_bonus
        
        # Projects boost confidence
        project_bonus = min(len(self.projects) * 3, 15)
        
        # Certifications boost confidence
        cert_bonus = min(len(self.certifications) * 2, 10)
        
        # Skills count boost
        skill_bonus = min(len(self.skills) * 0.5, 5)
        
        total_score = base_score + experience_bonus + project_bonus + cert_bonus + skill_bonus
        
        return min(round(total_score, 2), 100.0)

    # ============== Existing Validators (unchanged) ==============

    @field_validator('skills', mode='before')
    @classmethod
    def parse_skills(cls, v: Any) -> list[str]:
        """Handle various skill formats from LLM"""
        if v is None:
            return []
        
        if isinstance(v, list):
            skills = []
            for item in v:
                if isinstance(item, str):
                    skills.append(item)
                elif isinstance(item, dict):
                    if 'name' in item:
                        if isinstance(item['name'], str) and 'items' not in item:
                            skills.append(item['name'])
                        if 'items' in item and isinstance(item['items'], list):
                            skills.extend([str(s) for s in item['items']])
                    if 'skill' in item:
                        skills.append(str(item['skill']))
                    if 'items' in item and 'name' not in item:
                        skills.extend([str(s) for s in item['items']])
            return skills
        
        if isinstance(v, str):
            import ast
            import json
            
            try:
                parsed = json.loads(v)
                return cls.parse_skills(parsed)
            except:
                pass
            
            try:
                parsed = ast.literal_eval(v)
                return cls.parse_skills(parsed)
            except:
                pass
            
            if ',' in v:
                return [s.strip() for s in v.split(',') if s.strip()]
            
            return [v] if v.strip() else []
        
        return []

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v and '@' not in str(v):
            return None
        return v
    
    @field_validator('experience', 'education', 'certifications', 'projects', 'gaps', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, str):
            return []
        if isinstance(v, list):
            return v
        return []
    
    # NEW: Validator for experience_metrics 👇
    @field_validator('experience_metrics', mode='before')
    @classmethod
    def parse_experience_metrics(cls, v: Any) -> ExperienceMetrics:
        """Handle various formats for experience_metrics"""
        if v is None:
            return ExperienceMetrics()
        if isinstance(v, ExperienceMetrics):
            return v
        if isinstance(v, dict):
            return ExperienceMetrics(**v)
        return ExperienceMetrics()

    # ============== Updated Classifier Format (with new fields) ==============

    def to_classifier_format(self) -> dict:
        """Convert to the format expected by classifier prompt"""
        return {
            "personal": {
                "name": self.name,
                "email": self.email,
                "phone": self.phone,
                "location": self.location,
                "linkedin": self.linkedin,
                "github": self.github,
            },
            "education": [
                {
                    "degree": edu.degree,
                    "institution": edu.institution,
                    "field": edu.field,
                    "graduation_year": edu.graduation_year or edu.end_year,
                }
                for edu in self.education
            ],
            "experience": [
                {
                    "title": exp.title,
                    "company": exp.company,
                    "start": exp.start_date,
                    "end": exp.end_date,
                    "type": exp.type or "unknown",
                    "duration": exp.duration,
                    "duration_months": exp.duration_months,  # NEW 👈
                }
                for exp in self.experience
            ],
            # NEW: Experience metrics section 👇
            "experience_metrics": {
                "total_full_time_months": self.experience_metrics.total_full_time_months,
                "total_internship_months": self.experience_metrics.total_internship_months,
                "total_contract_months": self.experience_metrics.total_contract_months,
                "total_freelance_months": self.experience_metrics.total_freelance_months,
                "candidate_status": self.candidate_status,
                "confidence_score": self.experience_confidence_score,
            },
            "projects": [
                {
                    "name": proj.name,
                    "tech_stack": proj.technologies or proj.tech_stack,
                    "outcome": proj.outcome or proj.description,
                }
                for proj in self.projects
            ],
            "skills": self.skills,
            "certifications": [cert.name for cert in self.certifications],
            "gaps": [
                {
                    "start": gap.start,
                    "end": gap.end,
                    "reason": gap.reason,
                }
                for gap in self.gaps
            ],
        }