"""
Main resume parser combining all extraction methods.
"""
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from parser.extractor import ResumeExtractor
from parser.preprocessor import ResumePreprocessor, ResumeSection
from parser.regex_parser import RegexParser
from parser.llm_parser import LLMParserWithRetry
from parser.validators import ResumeValidator
from models.resume import Resume, Experience, ExperienceMetrics


class ResumeParser:
    """
    Main resume parser that combines:
    1. Text extraction from files
    2. Preprocessing and section detection
    3. Regex-based extraction (for validation)
    4. LLM-based parsing
    5. Post-processing validation
    """
    
    def __init__(
        self,
        llm_model: str = "llama3.1",
        llm_base_url: str = "http://localhost:11434",
        use_hybrid: bool = True,  # Combine regex + LLM
    ):
        self.extractor = ResumeExtractor()
        self.preprocessor = ResumePreprocessor()
        self.regex_parser = RegexParser()
        self.llm_parser = LLMParserWithRetry(model=llm_model, base_url=llm_base_url)
        self.validator = ResumeValidator()
        self.use_hybrid = use_hybrid
    
    def parse_file(self, file_path: str | Path) -> Tuple[Resume, Dict[str, Any]]:
        """
        Parse resume from file.
        
        Returns:
            Tuple of (Resume model, metadata dict)
        """
        # Step 1: Extract text from file
        text, extraction_meta = self.extractor.extract(file_path)
        
        if not text:
            raise ValueError("Failed to extract text from file")
        
        # Step 2: Parse text
        resume, parse_meta = self.parse_text(text)
        
        # Combine metadata
        metadata = {
            **extraction_meta,
            **parse_meta,
        }
        
        return resume, metadata
    
    def parse_bytes(self, file_bytes: bytes, file_type: str) -> Tuple[Resume, Dict[str, Any]]:
        """
        Parse resume from bytes.
        
        Returns:
            Tuple of (Resume model, metadata dict)
        """
        # Step 1: Extract text
        text, extraction_meta = self.extractor.extract_from_bytes(file_bytes, file_type)
        
        if not text:
            raise ValueError("Failed to extract text from file")
        
        # Step 2: Parse text
        resume, parse_meta = self.parse_text(text)
        
        metadata = {
            **extraction_meta,
            **parse_meta,
        }
        
        return resume, metadata
    
    def parse_text(self, text: str) -> Tuple[Resume, Dict[str, Any]]:
        """
        Parse resume from text.
        
        Returns:
            Tuple of (Resume model, metadata dict)
        """
        metadata = {
            "parsed_at": datetime.now().isoformat(),
            "text_length": len(text),
        }
        
        # Step 1: Preprocess text
        preprocessed = self.preprocessor.preprocess(text)
        metadata["sections_detected"] = [s.section_type.value for s in preprocessed["sections"]]
        
        # Step 2: Regex extraction (for validation/enhancement)
        regex_data = {}
        if self.use_hybrid:
            regex_data = {
                "contact": self.regex_parser.extract_contact_info(text),
                "skills": self.regex_parser.extract_skills(text),
                "dates": self.regex_parser.extract_dates(text),
            }
            metadata["regex_skills_count"] = len(regex_data["skills"])
        
        # Step 3: LLM parsing
        llm_result = self.llm_parser.parse(text)
        
        if "_parse_error" in llm_result:
            metadata["llm_error"] = llm_result["_parse_error"]
            # Try to build resume from regex data as fallback
            llm_result = self._build_fallback_result(preprocessed, regex_data)
        
        # Step 4: Enhance LLM result with regex data
        if self.use_hybrid:
            llm_result = self._enhance_with_regex(llm_result, regex_data, preprocessed)
        
        # Step 5: Validate and build Resume model
        try:
            resume = Resume.model_validate(llm_result)
            resume.raw_text = text
        except Exception as e:
            metadata["validation_error"] = str(e)
            # Try with cleaned data
            cleaned = self._clean_llm_result(llm_result)
            resume = Resume.model_validate(cleaned)
            resume.raw_text = text
        
        # Step 6: Post-validation
        validation_report = resume.get_validation_report()
        metadata["validation"] = validation_report
        
        return resume, metadata
    
    def _enhance_with_regex(
        self,
        llm_result: Dict[str, Any],
        regex_data: Dict[str, Any],
        preprocessed: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance LLM result with regex extracted data."""
        
        # Enhance contact info
        if regex_data.get("contact"):
            contact = regex_data["contact"]
            if not llm_result.get("email") and contact.get("email"):
                llm_result["email"] = contact["email"]
            if not llm_result.get("phone") and contact.get("phone"):
                llm_result["phone"] = contact["phone"]
            if not llm_result.get("linkedin") and contact.get("linkedin"):
                llm_result["linkedin"] = contact["linkedin"]
            if not llm_result.get("github") and contact.get("github"):
                llm_result["github"] = contact["github"]
            if not llm_result.get("name") and contact.get("name"):
                llm_result["name"] = contact["name"]
        
        # Enhance skills (merge and deduplicate)
        llm_skills = set(llm_result.get("skills", []))
        regex_skills = set(regex_data.get("skills", []))
        merged_skills = llm_skills | regex_skills
        llm_result["skills"] = sorted(list(merged_skills))
        
        # Validate experience types using regex
        experiences = llm_result.get("experience", [])
        for exp in experiences:
            if isinstance(exp, dict):
                title = exp.get("title", "")
                company = exp.get("company", "")
                detected_type = self.regex_parser.detect_experience_type(title, company)
                
                # Override if LLM got it wrong
                current_type = exp.get("type", "unknown")
                if current_type == "unknown" or current_type == "full-time":
                    if detected_type in ["internship", "contract", "freelance"]:
                        exp["type"] = detected_type
                
                # Recalculate duration if needed
                start = exp.get("start_date", "")
                end = exp.get("end_date", "")
                if start and end:
                    calculated = self.regex_parser.calculate_duration_months(start, end)
                    current = exp.get("duration_months", 0)
                    if current == 0 or abs(current - calculated) > 3:
                        exp["duration_months"] = calculated
        
        return llm_result
    
    def _build_fallback_result(
        self,
        preprocessed: Dict[str, Any],
        regex_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build fallback result when LLM fails."""
        contact = regex_data.get("contact", {})
        
        return {
            "name": contact.get("name", ""),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "linkedin": contact.get("linkedin"),
            "github": contact.get("github"),
            "location": contact.get("location"),
            "summary": preprocessed.get("section_texts", {}).get("summary"),
            "skills": regex_data.get("skills", []),
            "experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "experience_metrics": {
                "total_full_time_months": 0,
                "total_internship_months": 0,
                "total_contract_months": 0,
                "total_freelance_months": 0,
            }
        }
    
    def _clean_llm_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean LLM result to fix common issues."""
        # Ensure required fields exist
        defaults = {
            "name": "",
            "email": None,
            "phone": None,
            "location": None,
            "linkedin": None,
            "github": None,
            "website": None,
            "summary": None,
            "skills": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "languages": [],
            "experience_metrics": {
                "total_full_time_months": 0,
                "total_internship_months": 0,
                "total_contract_months": 0,
                "total_freelance_months": 0,
            }
        }
        
        for key, default in defaults.items():
            if key not in result or result[key] is None:
                if isinstance(default, list):
                    result[key] = []
                elif isinstance(default, dict):
                    result[key] = default.copy()
                else:
                    result[key] = default
        
        # Clean experience entries
        cleaned_exp = []
        for exp in result.get("experience", []):
            if isinstance(exp, dict) and exp.get("company"):
                cleaned_exp.append({
                    "company": exp.get("company", ""),
                    "title": exp.get("title", ""),
                    "type": exp.get("type", "unknown"),
                    "location": exp.get("location"),
                    "start_date": exp.get("start_date"),
                    "end_date": exp.get("end_date"),
                    "duration": exp.get("duration"),
                    "duration_months": exp.get("duration_months", 0),
                    "responsibilities": exp.get("responsibilities", []),
                })
        result["experience"] = cleaned_exp
        
        return result


# Convenience function
def parse_resume(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_type: Optional[str] = None,
    text: Optional[str] = None,
    model: str = "llama3.1"
) -> Tuple[Resume, Dict[str, Any]]:
    """
    Convenience function to parse a resume.
    
    Args:
        file_path: Path to resume file
        file_bytes: Resume file as bytes
        file_type: File type (required if using file_bytes)
        text: Resume text directly
        model: LLM model to use
    
    Returns:
        Tuple of (Resume model, metadata dict)
    """
    parser = ResumeParser(llm_model=model)
    
    if file_path:
        return parser.parse_file(file_path)
    elif file_bytes and file_type:
        return parser.parse_bytes(file_bytes, file_type)
    elif text:
        return parser.parse_text(text)
    else:
        raise ValueError("Must provide file_path, file_bytes+file_type, or text")