"""
Post-processing validation and correction for parsed resumes.
"""
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher
import re


class ResumeValidator:
    """Validate and correct parsed resume data."""
    
    # Skills that should be normalized
    SKILL_NORMALIZATIONS = {
        'js': 'JavaScript',
        'javascript': 'JavaScript',
        'ts': 'TypeScript',
        'typescript': 'TypeScript',
        'py': 'Python',
        'python': 'Python',
        'node': 'Node.js',
        'nodejs': 'Node.js',
        'node.js': 'Node.js',
        'react.js': 'React',
        'reactjs': 'React',
        'vue.js': 'Vue.js',
        'vuejs': 'Vue.js',
        'angular.js': 'Angular',
        'angularjs': 'Angular',
        'k8s': 'Kubernetes',
        'kubernetes': 'Kubernetes',
        'postgres': 'PostgreSQL',
        'postgresql': 'PostgreSQL',
        'mongo': 'MongoDB',
        'mongodb': 'MongoDB',
        'aws': 'AWS',
        'gcp': 'Google Cloud',
        'google cloud': 'Google Cloud',
        'azure': 'Azure',
        'c#': 'C#',
        'c++': 'C++',
        'golang': 'Go',
        '.net': '.NET',
        'dotnet': '.NET',
    }
    
    # Experience type keywords for validation
    INTERNSHIP_KEYWORDS = ['intern', 'internship', 'trainee', 'apprentice', 'co-op', 'coop', 'fellow']
    CONTRACT_KEYWORDS = ['contract', 'contractor', 'consultant', 'consulting', 'c2c', 'w2', 'via ', 'client:']
    FREELANCE_KEYWORDS = ['freelance', 'freelancer', 'self-employed', 'self employed', 'independent']
    
    def __init__(self):
        self.issues: List[str] = []
        self.corrections: List[str] = []
    
    def validate(self, resume_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Validate and correct resume data.
        
        Returns:
            Tuple of (corrected_data, validation_report)
        """
        self.issues = []
        self.corrections = []
        
        # Validate contact info
        resume_data = self._validate_contact(resume_data)
        
        # Validate experience
        resume_data = self._validate_experience(resume_data)
        
        # Validate education
        resume_data = self._validate_education(resume_data)
        
        # Validate skills
        resume_data = self._validate_skills(resume_data)
        
        # Validate certifications
        resume_data = self._validate_certifications(resume_data)
        
        # Validate projects
        resume_data = self._validate_projects(resume_data)
        
        # Remove duplicates
        resume_data = self._remove_duplicates(resume_data)
        
        # Recalculate metrics
        resume_data = self._recalculate_metrics(resume_data)
        
        report = {
            "is_valid": len(self.issues) == 0,
            "issues": self.issues,
            "corrections": self.corrections,
            "experience_count": len(resume_data.get("experience", [])),
            "education_count": len(resume_data.get("education", [])),
            "skills_count": len(resume_data.get("skills", [])),
        }
        
        return resume_data, report
    
    def _validate_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact information."""
        # Validate email
        email = data.get("email")
        if email:
            email = str(email).strip().lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                self.issues.append(f"Invalid email format: {email}")
                data["email"] = None
            else:
                data["email"] = email
        
        # Validate phone
        phone = data.get("phone")
        if phone:
            digits = re.sub(r'[^\d]', '', str(phone))
            if len(digits) < 10:
                self.issues.append(f"Phone number too short: {phone}")
            elif len(digits) > 15:
                self.issues.append(f"Phone number too long: {phone}")
        
        # Check for name
        name = data.get("name", "").strip()
        if not name:
            self.issues.append("Missing candidate name")
        elif len(name) < 2:
            self.issues.append(f"Name too short: {name}")
        else:
            # Clean name
            data["name"] = self._clean_name(name)
        
        # Validate LinkedIn URL
        linkedin = data.get("linkedin")
        if linkedin:
            linkedin = str(linkedin).strip().lower()
            if "linkedin" not in linkedin:
                data["linkedin"] = f"linkedin.com/in/{linkedin}"
        
        # Validate GitHub URL
        github = data.get("github")
        if github:
            github = str(github).strip().lower()
            if "github" not in github:
                data["github"] = f"github.com/{github}"
        
        return data
    
    def _clean_name(self, name: str) -> str:
        """Clean and format name."""
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Remove common prefixes/suffixes that aren't part of name
        remove_patterns = [
            r'^(mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?)\s+',
            r'\s+(jr\.?|sr\.?|ii|iii|iv|phd|md)$',
        ]
        
        for pattern in remove_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Title case
        words = name.split()
        formatted = []
        for word in words:
            if word.lower() in ['van', 'von', 'de', 'la', 'del']:
                formatted.append(word.lower())
            else:
                formatted.append(word.capitalize())
        
        return " ".join(formatted)
    
    def _validate_experience(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate experience entries."""
        experiences = data.get("experience", [])
        
        if not isinstance(experiences, list):
            data["experience"] = []
            self.corrections.append("Experience: Converted to empty list")
            return data
        
        validated = []
        
        for i, exp in enumerate(experiences):
            if not isinstance(exp, dict):
                self.issues.append(f"Experience #{i+1}: Invalid format (not a dict)")
                continue
            
            # Must have company or title
            company = str(exp.get("company", "")).strip()
            title = str(exp.get("title", "")).strip()
            
            if not company and not title:
                self.issues.append(f"Experience #{i+1}: Missing both company and title")
                continue
            
            exp["company"] = company
            exp["title"] = title
            
            # Validate and correct type
            exp = self._validate_experience_type(exp, i)
            
            # Validate dates
            exp = self._validate_experience_dates(exp, i)
            
            # Validate responsibilities
            responsibilities = exp.get("responsibilities", [])
            if isinstance(responsibilities, str):
                responsibilities = [r.strip() for r in responsibilities.split('\n') if r.strip()]
                exp["responsibilities"] = responsibilities
                self.corrections.append(f"Experience #{i+1}: Converted responsibilities to list")
            elif not isinstance(responsibilities, list):
                exp["responsibilities"] = []
            else:
                # Clean each responsibility
                exp["responsibilities"] = [
                    str(r).strip() for r in responsibilities 
                    if r and str(r).strip()
                ]
            
            validated.append(exp)
        
        data["experience"] = validated
        return data
    
    def _validate_experience_type(self, exp: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validate and correct experience type."""
        title = str(exp.get("title", "")).lower()
        company = str(exp.get("company", "")).lower()
        combined = f"{title} {company}"
        
        current_type = str(exp.get("type", "")).lower()
        detected_type = "full-time"
        
        # Detect correct type
        if any(kw in combined for kw in self.INTERNSHIP_KEYWORDS):
            detected_type = "internship"
        elif any(kw in combined for kw in self.CONTRACT_KEYWORDS):
            detected_type = "contract"
        elif any(kw in combined for kw in self.FREELANCE_KEYWORDS):
            detected_type = "freelance"
        
        # Valid types
        valid_types = ["full-time", "internship", "contract", "freelance", "part-time", "unknown"]
        
        if current_type not in valid_types:
            exp["type"] = detected_type
            self.corrections.append(f"Experience #{index+1}: Changed type from '{current_type}' to '{detected_type}'")
        elif current_type in ["unknown", "full-time"] and detected_type != "full-time":
            # Override if we detected a more specific type
            exp["type"] = detected_type
            self.corrections.append(f"Experience #{index+1}: Detected type as '{detected_type}'")
        
        return exp
    
    def _validate_experience_dates(self, exp: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Validate experience dates and duration."""
        start_date = exp.get("start_date")
        end_date = exp.get("end_date")
        duration_months = exp.get("duration_months", 0)
        
        # Ensure duration_months is integer
        if not isinstance(duration_months, int):
            try:
                duration_months = int(float(duration_months))
            except (ValueError, TypeError):
                duration_months = 0
        
        # Calculate duration from dates if possible
        if start_date and end_date:
            calculated = self._calculate_months(start_date, end_date)
            
            if calculated > 0:
                # If current duration is 0 or significantly different, use calculated
                if duration_months == 0:
                    exp["duration_months"] = calculated
                    self.corrections.append(f"Experience #{index+1}: Calculated duration as {calculated} months")
                elif abs(duration_months - calculated) > 3:
                    exp["duration_months"] = calculated
                    self.corrections.append(f"Experience #{index+1}: Corrected duration from {duration_months} to {calculated} months")
            elif duration_months == 0:
                self.issues.append(f"Experience #{index+1}: Could not calculate duration from dates")
        elif duration_months == 0:
            self.issues.append(f"Experience #{index+1}: Missing dates and duration")
        
        exp["duration_months"] = max(0, exp.get("duration_months", 0))
        
        return exp
    
    def _calculate_months(self, start_str: str, end_str: str) -> int:
        """Calculate months between two date strings."""
        try:
            start = self._parse_date(start_str)
            
            if not start:
                return 0
            
            # Handle "Present" or "Current"
            end_lower = str(end_str).strip().lower()
            if end_lower in ['present', 'current', 'now', 'ongoing']:
                end = datetime.now()
            else:
                end = self._parse_date(end_str)
            
            if not end:
                return 0
            
            if end < start:
                return 0
            
            months = (end.year - start.year) * 12 + (end.month - start.month) + 1
            return max(1, months)
        
        except Exception:
            return 0
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Common formats
        formats = [
            '%b %Y',        # Jan 2021
            '%B %Y',        # January 2021
            '%b. %Y',       # Jan. 2021
            '%m/%Y',        # 01/2021
            '%Y-%m',        # 2021-01
            '%Y',           # 2021
            '%m-%Y',        # 01-2021
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try extracting year and month with regex
        month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{4})', date_str, re.IGNORECASE)
        if month_match:
            month_abbr = month_match.group(1)[:3].title()
            year = month_match.group(2)
            try:
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
        
        return None
    
    def _validate_education(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate education entries."""
        education = data.get("education", [])
        
        if not isinstance(education, list):
            data["education"] = []
            self.corrections.append("Education: Converted to empty list")
            return data
        
        validated = []
        
        for i, edu in enumerate(education):
            if not isinstance(edu, dict):
                self.issues.append(f"Education #{i+1}: Invalid format")
                continue
            
            institution = str(edu.get("institution", "")).strip()
            degree = str(edu.get("degree", "")).strip()
            
            # Must have institution or degree
            if not institution and not degree:
                self.issues.append(f"Education #{i+1}: Missing both institution and degree")
                continue
            
            edu["institution"] = institution
            edu["degree"] = degree
            edu["field"] = str(edu.get("field", "")).strip() or None
            
            # Validate graduation year
            grad_year = edu.get("graduation_year")
            if grad_year is not None:
                try:
                    grad_year = int(grad_year)
                    if 1950 <= grad_year <= datetime.now().year + 10:
                        edu["graduation_year"] = grad_year
                    else:
                        edu["graduation_year"] = None
                        self.corrections.append(f"Education #{i+1}: Invalid graduation year removed")
                except (ValueError, TypeError):
                    # Try to extract from string
                    year_match = re.search(r'(19|20)\d{2}', str(grad_year))
                    if year_match:
                        edu["graduation_year"] = int(year_match.group(0))
                    else:
                        edu["graduation_year"] = None
            
            # Try to extract graduation year from end_year if missing
            if edu.get("graduation_year") is None and edu.get("end_year"):
                year_match = re.search(r'(19|20)\d{2}', str(edu["end_year"]))
                if year_match:
                    edu["graduation_year"] = int(year_match.group(0))
                    self.corrections.append(f"Education #{i+1}: Extracted graduation year from end_year")
            
            validated.append(edu)
        
        data["education"] = validated
        return data
    
    def _validate_skills(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean skills."""
        skills = data.get("skills", [])
        
        if not isinstance(skills, list):
            data["skills"] = []
            self.corrections.append("Skills: Converted to empty list")
            return data
        
        # Flatten if nested
        flat_skills = []
        for skill in skills:
            if isinstance(skill, str):
                flat_skills.append(skill.strip())
            elif isinstance(skill, dict):
                # Handle nested objects
                if "name" in skill:
                    flat_skills.append(str(skill["name"]).strip())
                elif "skill" in skill:
                    flat_skills.append(str(skill["skill"]).strip())
                elif "items" in skill and isinstance(skill["items"], list):
                    for item in skill["items"]:
                        flat_skills.append(str(item).strip())
            elif isinstance(skill, list):
                for item in skill:
                    flat_skills.append(str(item).strip())
        
        # Normalize and deduplicate
        normalized = []
        seen = set()
        
        for skill in flat_skills:
            if not skill or len(skill) < 2 or len(skill) > 50:
                continue
            
            # Normalize skill name
            skill_lower = skill.lower().strip()
            normalized_name = self.SKILL_NORMALIZATIONS.get(skill_lower, skill)
            
            # Skip if already seen (case-insensitive)
            if normalized_name.lower() in seen:
                continue
            
            seen.add(normalized_name.lower())
            normalized.append(normalized_name)
        
        if len(normalized) != len(flat_skills):
            self.corrections.append(f"Skills: Cleaned from {len(flat_skills)} to {len(normalized)} items")
        
        data["skills"] = sorted(normalized)
        return data
    
    def _validate_certifications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate certifications."""
        certifications = data.get("certifications", [])
        
        if not isinstance(certifications, list):
            data["certifications"] = []
            return data
        
        validated = []
        
        for cert in certifications:
            if not isinstance(cert, dict):
                continue
            
            name = str(cert.get("name", "")).strip()
            if not name:
                continue
            
            validated.append({
                "name": name,
                "issuer": str(cert.get("issuer", "")).strip() or None,
                "date": str(cert.get("date", "")).strip() or None,
            })
        
        data["certifications"] = validated
        return data
    
    def _validate_projects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate projects."""
        projects = data.get("projects", [])
        
        if not isinstance(projects, list):
            data["projects"] = []
            return data
        
        validated = []
        
        for proj in projects:
            if not isinstance(proj, dict):
                continue
            
            name = str(proj.get("name", "")).strip()
            if not name:
                continue
            
            # Ensure technologies is a list
            tech = proj.get("technologies", [])
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]
            elif not isinstance(tech, list):
                tech = []
            
            validated.append({
                "name": name,
                "description": str(proj.get("description", "")).strip() or None,
                "technologies": tech,
                "url": str(proj.get("url", "")).strip() or None,
            })
        
        data["projects"] = validated
        return data
    
    def _remove_duplicates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate entries."""
        # Remove duplicate experiences
        experiences = data.get("experience", [])
        unique_exp = []
        seen_keys = set()
        
        for exp in experiences:
            # Create unique key
            key = self._create_experience_key(exp)
            
            if key in seen_keys:
                self.corrections.append(f"Removed duplicate experience: {exp.get('company')} - {exp.get('title')}")
                continue
            
            # Also check for similar entries
            is_duplicate = False
            for existing in unique_exp:
                if self._are_experiences_similar(exp, existing):
                    is_duplicate = True
                    self.corrections.append(f"Removed similar experience: {exp.get('company')} - {exp.get('title')}")
                    break
            
            if not is_duplicate:
                seen_keys.add(key)
                unique_exp.append(exp)
        
        data["experience"] = unique_exp
        
        # Remove duplicate education
        education = data.get("education", [])
        unique_edu = []
        seen_edu = set()
        
        for edu in education:
            key = f"{edu.get('institution', '').lower()}|{edu.get('degree', '').lower()}"
            if key not in seen_edu:
                seen_edu.add(key)
                unique_edu.append(edu)
        
        data["education"] = unique_edu
        
        return data
    
    def _create_experience_key(self, exp: Dict[str, Any]) -> str:
        """Create unique key for experience."""
        company = str(exp.get("company", "")).lower().strip()
        title = str(exp.get("title", "")).lower().strip()
        start = str(exp.get("start_date", "")).lower().strip()
        
        # Normalize company name
        company = re.sub(r'[^\w\s]', '', company)
        company = ' '.join(company.split())
        
        # Normalize title
        title = re.sub(r'[^\w\s]', '', title)
        title = ' '.join(title.split())
        
        return f"{company}|{title}|{start}"
    
    def _are_experiences_similar(self, exp1: Dict[str, Any], exp2: Dict[str, Any]) -> bool:
        """Check if two experiences are similar (likely duplicates)."""
        company1 = str(exp1.get("company", "")).lower()
        company2 = str(exp2.get("company", "")).lower()
        title1 = str(exp1.get("title", "")).lower()
        title2 = str(exp2.get("title", "")).lower()
        
        # Check company similarity
        company_ratio = SequenceMatcher(None, company1, company2).ratio()
        title_ratio = SequenceMatcher(None, title1, title2).ratio()
        
        # Similar company AND similar title = likely duplicate
        if company_ratio > 0.8 and title_ratio > 0.8:
            # Also check dates
            start1 = str(exp1.get("start_date", ""))
            start2 = str(exp2.get("start_date", ""))
            
            if start1 and start2:
                # Extract years
                year1 = re.search(r'(19|20)\d{2}', start1)
                year2 = re.search(r'(19|20)\d{2}', start2)
                
                if year1 and year2:
                    return abs(int(year1.group(0)) - int(year2.group(0))) <= 1
            
            return True
        
        return False
    
    def _recalculate_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recalculate experience metrics from individual experiences."""
        experiences = data.get("experience", [])
        
        metrics = {
            "total_full_time_months": 0,
            "total_internship_months": 0,
            "total_contract_months": 0,
            "total_freelance_months": 0,
        }
        
        for exp in experiences:
            duration = exp.get("duration_months", 0)
            if not isinstance(duration, int):
                try:
                    duration = int(duration)
                except (ValueError, TypeError):
                    duration = 0
            
            exp_type = str(exp.get("type", "full-time")).lower()
            
            if exp_type == "full-time":
                metrics["total_full_time_months"] += duration
            elif exp_type == "internship":
                metrics["total_internship_months"] += duration
            elif exp_type == "contract":
                metrics["total_contract_months"] += duration
            elif exp_type == "freelance":
                metrics["total_freelance_months"] += duration
            elif exp_type == "part-time":
                # Count part-time as half
                metrics["total_full_time_months"] += duration // 2
            else:
                # Unknown - assume full-time
                metrics["total_full_time_months"] += duration
        
        # Check if recalculated differs from provided
        provided = data.get("experience_metrics", {})
        if isinstance(provided, dict):
            for key in metrics:
                provided_val = provided.get(key, 0)
                if provided_val != metrics[key]:
                    self.corrections.append(f"Metrics: Corrected {key} from {provided_val} to {metrics[key]}")
        
        data["experience_metrics"] = metrics
        
        return data