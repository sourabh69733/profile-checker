# utils/validator.py
import re
from typing import Optional
from models.resume import Resume

class ResumeValidator:
    """Validate and enhance parsed resume data"""
    
    def validate(self, resume: Resume) -> Resume:
        """Validate and clean resume data"""
        
        # Validate email
        if resume.email:
            resume.email = self._validate_email(resume.email)
        
        # Validate phone
        if resume.phone:
            resume.phone = self._validate_phone(resume.phone)
        
        # Validate URLs
        if resume.linkedin:
            resume.linkedin = self._validate_url(resume.linkedin, 'linkedin')
        if resume.github:
            resume.github = self._validate_url(resume.github, 'github')
        
        # Calculate confidence score
        resume.parse_confidence = self._calculate_confidence(resume)
        
        return resume
    
    def _validate_email(self, email: str) -> Optional[str]:
        """Validate email format"""
        email = email.strip().lower()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return email
        return None
    
    def _validate_phone(self, phone: str) -> Optional[str]:
        """Validate and normalize phone number"""
        # Remove all non-digit characters except +
        digits = re.sub(r'[^\d+]', '', phone)
        
        # Check minimum length
        if len(digits) < 10:
            return None
        
        return phone.strip()
    
    def _validate_url(self, url: str, platform: str) -> Optional[str]:
        """Validate URL format"""
        url = url.strip()
        
        # Add https if missing
        if not url.startswith('http'):
            url = f"https://{url}"
        
        # Platform-specific validation
        if platform == 'linkedin' and 'linkedin.com' not in url:
            return None
        if platform == 'github' and 'github.com' not in url:
            return None
        
        return url
    
    def _calculate_confidence(self, resume: Resume) -> float:
        """Calculate parsing confidence score (0-1)"""
        score = 0.0
        checks = 0
        
        # Essential fields
        if resume.name and len(resume.name) > 1:
            score += 1
        checks += 1
        
        if resume.email:
            score += 1
        checks += 1
        
        # Experience
        if resume.experience and len(resume.experience) > 0:
            score += 1
            # Check experience quality
            valid_exp = sum(1 for e in resume.experience if e.company and e.title)
            score += min(valid_exp / max(len(resume.experience), 1), 1)
            checks += 1
        checks += 1
        
        # Education
        if resume.education and len(resume.education) > 0:
            score += 1
        checks += 1
        
        # Skills
        if resume.skills and len(resume.skills) > 2:
            score += 1
        checks += 1
        
        return round(score / checks, 2)