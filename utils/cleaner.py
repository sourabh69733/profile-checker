# utils/cleaner.py
import re
from typing import Optional

class TextCleaner:
    """Clean and normalize extracted resume text"""
    
    def clean(self, text: str) -> str:
        """Apply all cleaning steps"""
        if not text:
            return ""
        
        text = self._normalize_whitespace(text)
        text = self._remove_special_chars(text)
        text = self._fix_common_issues(text)
        text = self._normalize_sections(text)
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and line breaks"""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Remove spaces at start/end of lines
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text
    
    def _remove_special_chars(self, text: str) -> str:
        """Remove problematic special characters"""
        # Keep common resume characters
        text = re.sub(r'[^\w\s@.\-+()/:,;&\'\"•·\n]', '', text)
        # Normalize bullets
        text = re.sub(r'[•·▪■□►]', '• ', text)
        return text
    
    def _fix_common_issues(self, text: str) -> str:
        """Fix common extraction issues"""
        # Fix split email addresses
        text = re.sub(r'(\w+)\s*@\s*(\w+)\s*\.\s*(\w+)', r'\1@\2.\3', text)
        # Fix split phone numbers
        text = re.sub(r'(\d{3})\s*[-.)]\s*(\d{3})\s*[-.)]\s*(\d{4})', r'\1-\2-\3', text)
        # Fix split URLs
        text = re.sub(r'(https?)\s*:\s*/\s*/\s*', r'\1://', text)
        return text
    
    def _normalize_sections(self, text: str) -> str:
        """Normalize common section headers"""
        # FIXED: Use re.IGNORECASE flag instead of inline (?i)
        section_patterns = {
            r'(work\s*)?experience': 'EXPERIENCE',
            r'education(al)?(\s*background)?': 'EDUCATION',
            r'(technical\s*)?skills': 'SKILLS',
            r'certifications?': 'CERTIFICATIONS',
            r'projects?': 'PROJECTS',
            r'(professional\s*)?summary': 'SUMMARY',
            r'objective': 'OBJECTIVE',
        }
        
        for pattern, replacement in section_patterns.items():
            # Use re.IGNORECASE and re.MULTILINE flags properly
            full_pattern = f'^{pattern}\\s*:?\\s*$'
            text = re.sub(
                full_pattern, 
                replacement, 
                text, 
                flags=re.MULTILINE | re.IGNORECASE
            )
        
        return text