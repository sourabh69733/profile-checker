"""
Preprocess resume text and detect sections.
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ResumeSection(Enum):
    """Resume section types."""
    HEADER = "header"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
    REFERENCES = "references"
    UNKNOWN = "unknown"


@dataclass
class SectionBlock:
    """A detected section in the resume."""
    section_type: ResumeSection
    title: str
    content: str
    start_pos: int
    end_pos: int
    confidence: float


class ResumePreprocessor:
    """Preprocess resume text and detect sections."""
    
    # Section header patterns
    SECTION_PATTERNS = {
        ResumeSection.SUMMARY: [
            r'(?i)^(professional\s+)?summary\s*:?\s*$',
            r'(?i)^(career\s+)?objective\s*:?\s*$',
            r'(?i)^profile\s*:?\s*$',
            r'(?i)^about(\s+me)?\s*:?\s*$',
            r'(?i)^overview\s*:?\s*$',
        ],
        ResumeSection.EXPERIENCE: [
            r'(?i)^(work\s+)?experience\s*:?\s*$',
            r'(?i)^(professional\s+)?experience\s*:?\s*$',
            r'(?i)^employment(\s+history)?\s*:?\s*$',
            r'(?i)^work\s+history\s*:?\s*$',
            r'(?i)^career\s+history\s*:?\s*$',
            r'(?i)^positions?\s+held\s*:?\s*$',
        ],
        ResumeSection.EDUCATION: [
            r'(?i)^education(al)?\s*(background|qualifications?)?\s*:?\s*$',
            r'(?i)^academic\s+(background|qualifications?)\s*:?\s*$',
            r'(?i)^qualifications?\s*:?\s*$',
        ],
        ResumeSection.SKILLS: [
            r'(?i)^(technical\s+)?skills?\s*:?\s*$',
            r'(?i)^(core\s+)?competenc(ies|e)\s*:?\s*$',
            r'(?i)^technologies?\s*:?\s*$',
            r'(?i)^tech\s+stack\s*:?\s*$',
            r'(?i)^expertise\s*:?\s*$',
            r'(?i)^proficienc(ies|y)\s*:?\s*$',
        ],
        ResumeSection.PROJECTS: [
            r'(?i)^(personal\s+)?projects?\s*:?\s*$',
            r'(?i)^(side\s+)?projects?\s*:?\s*$',
            r'(?i)^portfolio\s*:?\s*$',
            r'(?i)^key\s+projects?\s*:?\s*$',
        ],
        ResumeSection.CERTIFICATIONS: [
            r'(?i)^certifications?\s*:?\s*$',
            r'(?i)^certificates?\s*:?\s*$',
            r'(?i)^licenses?\s*(&\s*certifications?)?\s*:?\s*$',
            r'(?i)^credentials?\s*:?\s*$',
            r'(?i)^professional\s+development\s*:?\s*$',
        ],
        ResumeSection.LANGUAGES: [
            r'(?i)^languages?\s*:?\s*$',
            r'(?i)^language\s+skills?\s*:?\s*$',
        ],
        ResumeSection.AWARDS: [
            r'(?i)^awards?\s*(&\s*honors?)?\s*:?\s*$',
            r'(?i)^honors?\s*(&\s*awards?)?\s*:?\s*$',
            r'(?i)^achievements?\s*:?\s*$',
            r'(?i)^recognition\s*:?\s*$',
        ],
        ResumeSection.PUBLICATIONS: [
            r'(?i)^publications?\s*:?\s*$',
            r'(?i)^papers?\s*:?\s*$',
            r'(?i)^research\s*:?\s*$',
        ],
        ResumeSection.REFERENCES: [
            r'(?i)^references?\s*:?\s*$',
        ],
    }
    
    # Contact info patterns
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
    LINKEDIN_PATTERN = r'(?:linkedin\.com/in/|linkedin:?\s*)([a-zA-Z0-9_-]+)'
    GITHUB_PATTERN = r'(?:github\.com/|github:?\s*)([a-zA-Z0-9_-]+)'
    URL_PATTERN = r'https?://[^\s<>"{}|\\^`$$$$]+'
    
    def __init__(self):
        self.sections: List[SectionBlock] = []
        self.contact_info: Dict[str, str] = {}
    
    def preprocess(self, text: str) -> Dict:
        """
        Preprocess resume text.
        
        Returns:
            Dict with cleaned text, sections, and contact info
        """
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract contact info
        self.contact_info = self._extract_contact_info(cleaned_text)
        
        # Detect sections
        self.sections = self._detect_sections(cleaned_text)
        
        # Get header (content before first section)
        header_content = self._extract_header(cleaned_text)
        
        return {
            "original_text": text,
            "cleaned_text": cleaned_text,
            "contact_info": self.contact_info,
            "sections": self.sections,
            "header": header_content,
            "section_texts": self._get_section_texts(),
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\t', ' ', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove bullet point variations and normalize
        text = re.sub(r'^[\s]*[•●○◦▪▸►‣⁃]\s*', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*[-–—]\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\*\s+', '• ', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information from text."""
        # Usually in first 500 chars
        header_text = text[:500]
        
        contact = {
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "website": None,
        }
        
        # Email
        email_match = re.search(self.EMAIL_PATTERN, header_text)
        if email_match:
            contact["email"] = email_match.group(0).lower()
        
        # Phone
        phone_match = re.search(self.PHONE_PATTERN, header_text)
        if phone_match:
            contact["phone"] = phone_match.group(0)
        
        # LinkedIn
        linkedin_match = re.search(self.LINKEDIN_PATTERN, header_text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"linkedin.com/in/{linkedin_match.group(1)}"
        
        # GitHub
        github_match = re.search(self.GITHUB_PATTERN, header_text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"github.com/{github_match.group(1)}"
        
        # Website (excluding linkedin/github)
        urls = re.findall(self.URL_PATTERN, header_text)
        for url in urls:
            if 'linkedin' not in url.lower() and 'github' not in url.lower():
                contact["website"] = url
                break
        
        return contact
    
    def _detect_sections(self, text: str) -> List[SectionBlock]:
        """Detect sections in resume text."""
        sections = []
        lines = text.split('\n')
        
        current_section_start = 0
        current_section_type = ResumeSection.HEADER
        current_section_title = "Header"
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # Skip empty lines
            if not stripped_line:
                continue
            
            # Check if this line is a section header
            detected_section, confidence = self._match_section_header(stripped_line)
            
            if detected_section and confidence > 0.7:
                # Save previous section
                if i > 0:
                    section_content = '\n'.join(lines[current_section_start:i]).strip()
                    if section_content:
                        sections.append(SectionBlock(
                            section_type=current_section_type,
                            title=current_section_title,
                            content=section_content,
                            start_pos=current_section_start,
                            end_pos=i,
                            confidence=0.9 if current_section_type != ResumeSection.HEADER else 1.0
                        ))
                
                # Start new section
                current_section_start = i + 1
                current_section_type = detected_section
                current_section_title = stripped_line
        
        # Add final section
        final_content = '\n'.join(lines[current_section_start:]).strip()
        if final_content:
            sections.append(SectionBlock(
                section_type=current_section_type,
                title=current_section_title,
                content=final_content,
                start_pos=current_section_start,
                end_pos=len(lines),
                confidence=0.9
            ))
        
        return sections
    
    def _match_section_header(self, line: str) -> Tuple[Optional[ResumeSection], float]:
        """Match a line against section header patterns."""
        line = line.strip()
        
        # Too long to be a header
        if len(line) > 50:
            return None, 0.0
        
        # Check against patterns
        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, line):
                    return section_type, 0.95
        
        # Fuzzy matching for variations
        line_lower = line.lower().strip(':').strip()
        
        fuzzy_matches = {
            'experience': ResumeSection.EXPERIENCE,
            'work': ResumeSection.EXPERIENCE,
            'employment': ResumeSection.EXPERIENCE,
            'education': ResumeSection.EDUCATION,
            'academic': ResumeSection.EDUCATION,
            'skills': ResumeSection.SKILLS,
            'technical': ResumeSection.SKILLS,
            'projects': ResumeSection.PROJECTS,
            'certifications': ResumeSection.CERTIFICATIONS,
            'certificates': ResumeSection.CERTIFICATIONS,
            'languages': ResumeSection.LANGUAGES,
            'awards': ResumeSection.AWARDS,
            'summary': ResumeSection.SUMMARY,
            'objective': ResumeSection.SUMMARY,
            'profile': ResumeSection.SUMMARY,
        }
        
        for keyword, section_type in fuzzy_matches.items():
            if keyword in line_lower and len(line_lower.split()) <= 4:
                return section_type, 0.75
        
        return None, 0.0
    
    def _extract_header(self, text: str) -> str:
        """Extract header content (name, contact, etc.)."""
        if not self.sections:
            return text[:500]
        
        first_section = self.sections[0]
        if first_section.section_type == ResumeSection.HEADER:
            return first_section.content
        
        # Content before first detected section
        lines = text.split('\n')
        header_lines = lines[:first_section.start_pos]
        return '\n'.join(header_lines).strip()
    
    def _get_section_texts(self) -> Dict[str, str]:
        """Get section texts as dictionary."""
        result = {}
        for section in self.sections:
            key = section.section_type.value
            if key in result:
                result[key] += '\n\n' + section.content
            else:
                result[key] = section.content
        return result
    
    def get_section(self, section_type: ResumeSection) -> Optional[str]:
        """Get content of a specific section type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section.content
        return None