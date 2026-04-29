"""
Resume Pydantic Models

Comprehensive models for parsed resume data with validation,
computed properties, and helper methods.
"""

from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
from typing import Optional, Any, Literal, List, Dict, ClassVar
from datetime import datetime
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from difflib import SequenceMatcher
import re
import json


# ============== Helper Functions ==============

def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime object."""
    if not date_str:
        return None
    
    date_str = str(date_str).strip().lower()
    
    # Handle "Present" or "Current"
    if date_str in ["present", "current", "now", "ongoing", "till date", "to date"]:
        return datetime.now()
    
    # Try common formats
    formats_to_try = [
        "%b %Y",       # Jan 2021
        "%B %Y",       # January 2021
        "%b. %Y",      # Jan. 2021
        "%m/%Y",       # 01/2021
        "%Y-%m",       # 2021-01
        "%Y",          # 2021
        "%m-%Y",       # 01-2021
        "%b %d, %Y",   # Jan 15, 2021
        "%B %d, %Y",   # January 15, 2021
        "%m/%d/%Y",    # 01/15/2021
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str.title(), fmt)
        except ValueError:
            continue
    
    # Try regex extraction
    month_match = re.search(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})',
        date_str,
        re.IGNORECASE
    )
    if month_match:
        try:
            month_abbr = month_match.group(1)[:3].title()
            year = month_match.group(2)
            return datetime.strptime(f"{month_abbr} {year}", '%b %Y')
        except ValueError:
            pass
    
    # Try just year
    year_match = re.search(r'(19|20)\d{2}', date_str)
    if year_match:
        try:
            return datetime.strptime(year_match.group(0), '%Y')
        except ValueError:
            pass
    
    # Try dateutil as fallback
    try:
        return date_parser.parse(date_str, fuzzy=True)
    except Exception:
        return None


def calculate_months_between(start_str: str, end_str: str) -> int:
    """Calculate months between two date strings."""
    start_date = parse_date_string(start_str)
    end_date = parse_date_string(end_str)
    
    if not start_date or not end_date:
        return 0
    
    if end_date < start_date:
        return 0
    
    diff = relativedelta(end_date, start_date)
    months = diff.years * 12 + diff.months
    
    # Add 1 to include both start and end months
    return max(1, months + 1)


def detect_experience_type(title: str, company: str = "") -> str:
    """Detect experience type from job title and company."""
    title_lower = (title or "").lower()
    company_lower = (company or "").lower()
    combined = f"{title_lower} {company_lower}"
    
    # Internship indicators (check first - highest priority)
    internship_keywords = [
        'intern', 'internship', 'trainee', 'apprentice', 
        'fellow', 'co-op', 'coop', 'summer intern', 'winter intern'
    ]
    if any(kw in title_lower for kw in internship_keywords):
        return "internship"
    
    # Contract indicators
    contract_keywords = [
        'contract', 'contractor', 'consultant', 'consulting', 
        'c2c', 'w2 contract', 'fixed-term', 'fixed term', 
        'via ', 'client:', 'staffing', 'temp ', 'temporary'
    ]
    if any(kw in combined for kw in contract_keywords):
        return "contract"
    
    # Freelance indicators
    freelance_keywords = [
        'freelance', 'freelancer', 'self-employed', 'self employed',
        'independent', 'own business', 'upwork', 'fiverr', 'toptal',
        'personal business', 'sole proprietor'
    ]
    if any(kw in combined for kw in freelance_keywords):
        return "freelance"
    
    # Part-time indicators
    parttime_keywords = ['part-time', 'part time', 'parttime', 'half-time']
    if any(kw in title_lower for kw in parttime_keywords):
        return "part-time"
    
    # Default to full-time
    return "full-time"


def normalize_string(s: str) -> str:
    """Normalize string for comparison."""
    if not s:
        return ""
    s = re.sub(r'[^\w\s]', '', s.lower())
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strings_similar(s1: str, s2: str, threshold: float = 0.85) -> bool:
    """Check if two strings are similar."""
    if not s1 or not s2:
        return False
    
    s1_norm = normalize_string(s1)
    s2_norm = normalize_string(s2)
    
    if s1_norm == s2_norm:
        return True
    
    ratio = SequenceMatcher(None, s1_norm, s2_norm).ratio()
    return ratio >= threshold


# ============== Experience Metrics Model ==============

class ExperienceMetrics(BaseModel):
    """Aggregated experience metrics by type."""
    
    total_full_time_months: int = Field(default=0, ge=0)
    total_internship_months: int = Field(default=0, ge=0)
    total_contract_months: int = Field(default=0, ge=0)
    total_freelance_months: int = Field(default=0, ge=0)
    
    @field_validator('*', mode='before')
    @classmethod
    def ensure_non_negative_int(cls, v):
        """Ensure all values are non-negative integers."""
        if v is None:
            return 0
        if isinstance(v, (int, float)):
            return max(0, int(v))
        if isinstance(v, str):
            try:
                return max(0, int(float(v)))
            except (ValueError, TypeError):
                return 0
        return 0
    
    @computed_field
    @property
    def total_professional_months(self) -> int:
        """Total months excluding internships (for experience level calculation)."""
        return self.total_full_time_months + self.total_contract_months + self.total_freelance_months
    
    @computed_field
    @property
    def total_all_months(self) -> int:
        """Total months including all experience types."""
        return (
            self.total_full_time_months + 
            self.total_internship_months + 
            self.total_contract_months + 
            self.total_freelance_months
        )
    
    @computed_field
    @property
    def experience_level(self) -> str:
        """Determine experience level based on professional months."""
        if self.total_professional_months >= 12:
            return "EXPERIENCED"
        return "FRESHER"
    
    @computed_field
    @property
    def experience_years(self) -> float:
        """Total professional experience in years."""
        return round(self.total_professional_months / 12, 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_full_time_months": self.total_full_time_months,
            "total_internship_months": self.total_internship_months,
            "total_contract_months": self.total_contract_months,
            "total_freelance_months": self.total_freelance_months,
            "total_professional_months": self.total_professional_months,
            "total_all_months": self.total_all_months,
            "experience_level": self.experience_level,
            "experience_years": self.experience_years,
        }


# ============== Experience Model ==============

class Experience(BaseModel):
    """Individual work experience entry."""
    
    company: str = ""
    title: str = ""
    type: Literal["full-time", "internship", "contract", "freelance", "part-time", "unknown"] = "unknown"
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    duration_months: int = Field(default=0, ge=0)
    responsibilities: List[str] = Field(default_factory=list)
    
    @field_validator('company', 'title', mode='before')
    @classmethod
    def clean_string_fields(cls, v):
        """Clean string fields."""
        if v is None:
            return ""
        return str(v).strip()
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        """Validate and normalize experience type."""
        valid_types = ["full-time", "internship", "contract", "freelance", "part-time", "unknown"]
        
        if v is None:
            return "unknown"
        
        v_str = str(v).lower().strip()
        
        # Handle common variations
        type_mapping = {
            "full_time": "full-time",
            "fulltime": "full-time",
            "permanent": "full-time",
            "regular": "full-time",
            "intern": "internship",
            "internships": "internship",
            "contractor": "contract",
            "consulting": "contract",
            "consultant": "contract",
            "freelancer": "freelance",
            "self-employed": "freelance",
            "self employed": "freelance",
            "part_time": "part-time",
            "parttime": "part-time",
        }
        
        if v_str in type_mapping:
            return type_mapping[v_str]
        
        if v_str in valid_types:
            return v_str
        
        return "unknown"
    
    @field_validator('duration_months', mode='before')
    @classmethod
    def validate_duration_months(cls, v):
        """Ensure duration_months is a valid non-negative integer."""
        if v is None:
            return 0
        if isinstance(v, int):
            return max(0, v)
        if isinstance(v, (str, float)):
            try:
                return max(0, int(float(v)))
            except (ValueError, TypeError):
                return 0
        return 0
    
    @field_validator('responsibilities', mode='before')
    @classmethod
    def validate_responsibilities(cls, v):
        """Ensure responsibilities is a list of strings."""
        if v is None:
            return []
        
        if isinstance(v, str):
            # Split by newlines or bullet points
            items = re.split(r'[\n•\-\*]', v)
            return [item.strip() for item in items if item.strip()]
        
        if isinstance(v, list):
            return [str(r).strip() for r in v if r and str(r).strip()]
        
        return []
    
    @model_validator(mode='after')
    def auto_detect_and_calculate(self):
        """Auto-detect type and calculate duration after validation."""
        # Auto-detect type if unknown
        if self.type == "unknown" and self.title:
            self.type = detect_experience_type(self.title, self.company)
        
        # Recalculate duration_months if dates are available
        if self.start_date and self.end_date:
            calculated = calculate_months_between(self.start_date, self.end_date)
            
            # Use calculated value if current is 0 or significantly different
            if self.duration_months == 0:
                self.duration_months = calculated
            elif calculated > 0 and abs(self.duration_months - calculated) > 3:
                self.duration_months = calculated
        
        return self
    
    def get_unique_key(self) -> str:
        """Generate unique key for deduplication."""
        company_norm = normalize_string(self.company)
        title_norm = normalize_string(self.title)
        start = normalize_string(self.start_date or "")
        return f"{company_norm}|{title_norm}|{start}"
    
    def is_similar_to(self, other: 'Experience') -> bool:
        """Check if this experience is similar to another (potential duplicate)."""
        company_match = strings_similar(self.company, other.company, 0.8)
        title_match = strings_similar(self.title, other.title, 0.8)
        
        if not (company_match and title_match):
            return False
        
        # Check date overlap
        if self.start_date and other.start_date:
            start1 = parse_date_string(self.start_date)
            start2 = parse_date_string(other.start_date)
            
            if start1 and start2:
                diff_months = abs((start1 - start2).days) / 30
                return diff_months < 3
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "company": self.company,
            "title": self.title,
            "type": self.type,
            "location": self.location,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration": self.duration,
            "duration_months": self.duration_months,
            "responsibilities": self.responsibilities,
        }


# ============== Education Model ==============

class Education(BaseModel):
    """Education entry."""
    
    institution: str = ""
    degree: str = ""
    field: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None
    
    @field_validator('institution', 'degree', mode='before')
    @classmethod
    def clean_string_fields(cls, v):
        """Clean string fields."""
        if v is None:
            return ""
        return str(v).strip()
    
    @field_validator('graduation_year', mode='before')
    @classmethod
    def parse_graduation_year(cls, v):
        """Parse graduation year to integer."""
        if v is None:
            return None
        
        if isinstance(v, int):
            return v if 1950 <= v <= 2100 else None
        
        if isinstance(v, str):
            # Try to extract year
            match = re.search(r'(19|20)\d{2}', v)
            if match:
                year = int(match.group())
                return year if 1950 <= year <= 2100 else None
        
        return None
    
    @model_validator(mode='after')
    def extract_graduation_year(self):
        """Extract graduation_year from end_year if not set."""
        if self.graduation_year is None and self.end_year:
            match = re.search(r'(19|20)\d{2}', str(self.end_year))
            if match:
                self.graduation_year = int(match.group())
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "institution": self.institution,
            "degree": self.degree,
            "field": self.field,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "graduation_year": self.graduation_year,
            "gpa": self.gpa,
        }


# ============== Certification Model ==============

class Certification(BaseModel):
    """Certification entry."""
    
    name: str = ""
    issuer: Optional[str] = None
    date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None
    
    @field_validator('name', mode='before')
    @classmethod
    def clean_name(cls, v):
        """Clean name field."""
        if v is None:
            return ""
        return str(v).strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "issuer": self.issuer,
            "date": self.date,
            "expiry_date": self.expiry_date,
            "credential_id": self.credential_id,
            "url": self.url,
        }


# ============== Project Model ==============

class Project(BaseModel):
    """Project entry."""
    
    name: str = ""
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    github_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    @field_validator('name', mode='before')
    @classmethod
    def clean_name(cls, v):
        """Clean name field."""
        if v is None:
            return ""
        return str(v).strip()
    
    @field_validator('technologies', mode='before')
    @classmethod
    def validate_technologies(cls, v):
        """Ensure technologies is a list of strings."""
        if v is None:
            return []
        
        if isinstance(v, str):
            return [t.strip() for t in v.split(',') if t.strip()]
        
        if isinstance(v, list):
            return [str(t).strip() for t in v if t and str(t).strip()]
        
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "technologies": self.technologies,
            "url": self.url,
            "github_url": self.github_url,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


# ============== Gap Model ==============

class Gap(BaseModel):
    """Employment gap entry."""
    
    start: Optional[str] = None
    end: Optional[str] = None
    duration_months: int = Field(default=0, ge=0)
    reason: Optional[str] = None
    
    @model_validator(mode='after')
    def calculate_duration(self):
        """Calculate duration if dates are available."""
        if self.start and self.end and self.duration_months == 0:
            self.duration_months = calculate_months_between(self.start, self.end)
        return self


# ============== Parsing Notes Model ==============

class ParsingNotes(BaseModel):
    """Metadata about the parsing process."""
    
    confidence: Literal["high", "medium", "low"] = "medium"
    issues: List[str] = Field(default_factory=list)
    corrections: List[str] = Field(default_factory=list)
    duplicates_removed: int = 0
    types_corrected: int = 0
    extraction_method: Optional[str] = None


# ============== Main Resume Model ==============

class Resume(BaseModel):
    """
    Main Resume Model
    
    Comprehensive model for parsed resume data with:
    - Automatic validation and correction
    - Computed properties for quick access
    - Helper methods for classification
    - Deduplication of experiences
    """
    
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
    skills: List[str] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    
    # Experience Metrics
    experience_metrics: ExperienceMetrics = Field(default_factory=ExperienceMetrics)
    
    # Optional Sections
    certifications: List[Certification] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    publications: List[str] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)
    
    # Metadata
    parsing_notes: ParsingNotes = Field(default_factory=ParsingNotes)
    raw_text: Optional[str] = None
    parsed_at: Optional[datetime] = None

    # ============== Field Validators ==============

    @field_validator('name', mode='before')
    @classmethod
    def clean_name(cls, v):
        """Clean and validate name."""
        if v is None:
            return ""
        name = str(v).strip()
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name
    
    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if v is None or not v:
            return None
        
        email = str(v).strip().lower()
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            return None
        
        return email
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        """Clean phone number."""
        if v is None or not v:
            return None
        
        phone = str(v).strip()
        
        # Basic validation - should have at least 10 digits
        digits = re.sub(r'[^\d]', '', phone)
        if len(digits) < 10:
            return None
        
        return phone
    
    @field_validator('skills', mode='before')
    @classmethod
    def parse_skills(cls, v: Any) -> List[str]:
        """Handle various skill formats and deduplicate."""
        if v is None:
            return []
        
        skills = []
        
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    skills.append(item.strip())
                elif isinstance(item, dict):
                    # Handle nested objects
                    if 'name' in item:
                        skills.append(str(item['name']).strip())
                    elif 'skill' in item:
                        skills.append(str(item['skill']).strip())
                    elif 'items' in item and isinstance(item['items'], list):
                        skills.extend([str(s).strip() for s in item['items']])
                elif isinstance(item, list):
                    skills.extend([str(s).strip() for s in item])
        
        elif isinstance(v, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(v)
                return cls.parse_skills(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Split by comma
            skills = [s.strip() for s in v.split(',') if s.strip()]
        
        # Deduplicate while preserving order (case-insensitive)
        seen = set()
        unique_skills = []
        for skill in skills:
            if skill and len(skill) >= 2 and skill.lower() not in seen:
                seen.add(skill.lower())
                unique_skills.append(skill)
        
        return unique_skills
    
    @field_validator('experience', 'education', 'certifications', 'projects', 'gaps', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Any) -> List:
        """Ensure list fields are proper lists."""
        if v is None:
            return []
        if isinstance(v, str):
            return []
        if isinstance(v, list):
            return v
        return []
    
    @field_validator('languages', 'awards', 'publications', mode='before')
    @classmethod
    def parse_string_list(cls, v: Any) -> List[str]:
        """Parse string list fields."""
        if v is None:
            return []
        
        if isinstance(v, list):
            return [str(item).strip() for item in v if item and str(item).strip()]
        
        if isinstance(v, str):
            return [s.strip() for s in v.split(',') if s.strip()]
        
        return []
    
    @field_validator('experience_metrics', mode='before')
    @classmethod
    def parse_experience_metrics(cls, v: Any) -> ExperienceMetrics:
        """Parse experience metrics."""
        if v is None:
            return ExperienceMetrics()
        if isinstance(v, ExperienceMetrics):
            return v
        if isinstance(v, dict):
            return ExperienceMetrics(**v)
        return ExperienceMetrics()
    
    @field_validator('parsing_notes', mode='before')
    @classmethod
    def parse_parsing_notes(cls, v: Any) -> ParsingNotes:
        """Parse parsing notes."""
        if v is None:
            return ParsingNotes()
        if isinstance(v, ParsingNotes):
            return v
        if isinstance(v, dict):
            return ParsingNotes(**v)
        return ParsingNotes()

    # ============== Model Validator ==============

    @model_validator(mode='after')
    def post_process_resume(self):
        """
        Post-process resume after all fields are validated:
        1. Remove duplicate experiences
        2. Correct experience types
        3. Recalculate experience metrics
        """
        issues = []
        corrections = []
        duplicates_removed = 0
        types_corrected = 0
        
        # Step 1: Deduplicate experiences
        unique_experiences = []
        seen_keys = set()
        
        for exp in self.experience:
            key = exp.get_unique_key()
            
            # Check for exact duplicate
            if key in seen_keys:
                duplicates_removed += 1
                corrections.append(f"Removed duplicate: {exp.company} - {exp.title}")
                continue
            
            # Check for similar entries
            is_duplicate = False
            for existing in unique_experiences:
                if exp.is_similar_to(existing):
                    is_duplicate = True
                    duplicates_removed += 1
                    corrections.append(f"Removed similar: {exp.company} - {exp.title}")
                    break
            
            if not is_duplicate:
                seen_keys.add(key)
                unique_experiences.append(exp)
        
        self.experience = unique_experiences
        
        # Step 2: Correct experience types
        for exp in self.experience:
            if exp.type == "unknown":
                original_type = exp.type
                exp.type = detect_experience_type(exp.title, exp.company)
                if exp.type != original_type:
                    types_corrected += 1
        
        # Step 3: Recalculate experience metrics
        full_time = 0
        internship = 0
        contract = 0
        freelance = 0
        
        for exp in self.experience:
            months = exp.duration_months
            
            if exp.type == "full-time":
                full_time += months
            elif exp.type == "internship":
                internship += months
            elif exp.type == "contract":
                contract += months
            elif exp.type == "freelance":
                freelance += months
            elif exp.type == "part-time":
                full_time += months // 2
            else:
                # Unknown - detect and add
                detected = detect_experience_type(exp.title, exp.company)
                if detected == "internship":
                    internship += months
                elif detected == "contract":
                    contract += months
                elif detected == "freelance":
                    freelance += months
                else:
                    full_time += months
        
        self.experience_metrics = ExperienceMetrics(
            total_full_time_months=full_time,
            total_internship_months=internship,
            total_contract_months=contract,
            total_freelance_months=freelance
        )
        
        # Step 4: Update parsing notes
        self.parsing_notes = ParsingNotes(
            confidence="high" if (duplicates_removed == 0 and types_corrected == 0) else "medium",
            issues=issues,
            corrections=corrections,
            duplicates_removed=duplicates_removed,
            types_corrected=types_corrected,
            extraction_method=self.parsing_notes.extraction_method if self.parsing_notes else None
        )
        
        # Step 5: Set parsed timestamp
        if not self.parsed_at:
            self.parsed_at = datetime.now()
        
        return self

    # ============== Computed Properties ==============

    @computed_field
    @property
    def candidate_status(self) -> str:
        """Classify candidate as FRESHER or EXPERIENCED."""
        return self.experience_metrics.experience_level
    
    @computed_field
    @property
    def total_experience_years(self) -> float:
        """Total professional experience in years."""
        return self.experience_metrics.experience_years
    
    @computed_field
    @property
    def total_jobs_count(self) -> int:
        """Total number of jobs."""
        return len(self.experience)
    
    @computed_field
    @property
    def has_education(self) -> bool:
        """Check if candidate has formal education."""
        return any(edu.degree or edu.institution for edu in self.education)
    
    @computed_field
    @property
    def has_work_experience(self) -> bool:
        """Check if candidate has any work experience."""
        return len(self.experience) > 0
    
    @computed_field
    @property
    def has_contact_info(self) -> bool:
        """Check if candidate has contact information."""
        return bool(self.email or self.phone)
    
    @computed_field
    @property
    def has_internship_only(self) -> bool:
        """Check if candidate has only internship experience."""
        if not self.experience:
            return False
        return all(exp.type == "internship" for exp in self.experience)
    
    @computed_field
    @property
    def has_contract_experience(self) -> bool:
        """Check if candidate has contract experience."""
        return any(exp.type == "contract" for exp in self.experience)
    
    @computed_field
    @property
    def has_freelance_experience(self) -> bool:
        """Check if candidate has freelance experience."""
        return any(exp.type == "freelance" for exp in self.experience)
    
    @computed_field
    @property
    def skills_count(self) -> int:
        """Number of skills."""
        return len(self.skills)

    # ============== Helper Methods ==============

    def get_experiences_by_type(self, exp_type: str) -> List[Experience]:
        """Get all experiences of a specific type."""
        return [exp for exp in self.experience if exp.type == exp_type]
    
    def get_latest_experience(self) -> Optional[Experience]:
        """Get the most recent experience."""
        for exp in self.experience:
            if exp.end_date and exp.end_date.lower() in ['present', 'current', 'now']:
                return exp
        
        return self.experience[0] if self.experience else None
    
    def get_latest_education(self) -> Optional[Education]:
        """Get the most recent education."""
        if not self.education:
            return None
        
        # Sort by graduation year descending
        sorted_edu = sorted(
            self.education,
            key=lambda x: x.graduation_year or 0,
            reverse=True
        )
        
        return sorted_edu[0] if sorted_edu else None
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Generate a validation report."""
        issues = list(self.parsing_notes.issues)
        
        # Check for potential problems
        if not self.name:
            issues.append("Missing candidate name")
        
        if not self.email and not self.phone:
            issues.append("Missing contact information (email and phone)")
        
        for i, exp in enumerate(self.experience):
            if not exp.start_date:
                issues.append(f"Experience #{i+1} ({exp.company}) missing start_date")
            if exp.duration_months == 0:
                issues.append(f"Experience #{i+1} ({exp.company}) has 0 duration")
            if exp.type == "unknown":
                issues.append(f"Experience #{i+1} ({exp.company}) has unknown type")
        
        # Verify metrics match
        calculated_total = sum(exp.duration_months for exp in self.experience)
        metrics_total = self.experience_metrics.total_all_months
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "corrections": self.parsing_notes.corrections,
            "metrics_match": abs(calculated_total - metrics_total) <= 2,
            "total_jobs": len(self.experience),
            "jobs_by_type": {
                "full_time": len([e for e in self.experience if e.type == "full-time"]),
                "internship": len([e for e in self.experience if e.type == "internship"]),
                "contract": len([e for e in self.experience if e.type == "contract"]),
                "freelance": len([e for e in self.experience if e.type == "freelance"]),
                "part_time": len([e for e in self.experience if e.type == "part-time"]),
                "unknown": len([e for e in self.experience if e.type == "unknown"]),
            },
            "duplicates_removed": self.parsing_notes.duplicates_removed,
            "types_corrected": self.parsing_notes.types_corrected,
            "has_contact_info": self.has_contact_info,
            "has_education": self.has_education,
            "has_experience": self.has_work_experience,
        }
    
    def to_classifier_format(self) -> Dict[str, Any]:
        """Convert to format expected by classifier prompt."""
        return {
            "personal": {
                "name": self.name,
                "email": self.email,
                "phone": self.phone,
                "location": self.location,
                "linkedin": self.linkedin,
                "github": self.github,
                "website": self.website,
            },
            "summary": self.summary,
            "skills": self.skills,
            "experience_metrics": self.experience_metrics.to_dict(),
            "experience": [exp.to_dict() for exp in self.experience],
            "education": [edu.to_dict() for edu in self.education],
            "certifications": [cert.to_dict() for cert in self.certifications],
            "projects": [proj.to_dict() for proj in self.projects],
            "languages": self.languages,
            "awards": self.awards,
            "candidate_status": self.candidate_status,
            "total_experience_years": self.total_experience_years,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire resume to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "linkedin": self.linkedin,
            "github": self.github,
            "website": self.website,
            "summary": self.summary,
            "skills": self.skills,
            "experience_metrics": self.experience_metrics.to_dict(),
            "experience": [exp.to_dict() for exp in self.experience],
            "education": [edu.to_dict() for edu in self.education],
            "certifications": [cert.to_dict() for cert in self.certifications],
            "projects": [proj.to_dict() for proj in self.projects],
            "languages": self.languages,
            "awards": self.awards,
            "publications": self.publications,
            "candidate_status": self.candidate_status,
            "total_experience_years": self.total_experience_years,
            "validation": self.get_validation_report(),
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)