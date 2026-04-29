import json
import ollama
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .prompts import CLASSIFICATION_PROMPT
from models.resume import Resume
from models.classification import (
    ClassificationResult, 
    Classification, 
    Scoring, 
    DomainEvidence,
    ExperienceLevel
)
from config import ParserConfig

class TimeoutError(Exception):
    """Custom timeout error"""
    pass

class ResumeClassifier:
    """Classify parsed resume for experience level and domain"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.client = ollama.Client(host=config.ollama_host)
    
    def classify(self, resume: Resume) -> ClassificationResult:
        """Classify a parsed resume"""
        
        # Convert resume to classifier input format
        input_json = resume.to_classifier_format()
        
        # print('input_json', resume)
        # Validate input
        if not self._is_valid_input(input_json):
            return ClassificationResult(
                classification=Classification(
                    experience_level=ExperienceLevel.FRESHER,
                    tech_domain="unknown",
                    confidence=0.0
                ),
                scoring=Scoring(),
                flags=["invalid_input"],
                domain_evidence=DomainEvidence(),
                summary="Invalid or empty resume data",
                error="invalid_input",
                message="Resume data is empty or malformed"
            )
        
        # Generate prompt
        # prompt = CLASSIFICATION_PROMPT.format(
        #     input_json=json.dumps(input_json, indent=2,)
        # )
        
        prompt = CLASSIFICATION_PROMPT.format(
            parsed_resume=json.dumps(resume.to_classifier_format(), indent=2),
            total_full_time_months=resume.experience_metrics.total_full_time_months,
            total_internship_months=resume.experience_metrics.total_internship_months,
            total_contract_months=resume.experience_metrics.total_contract_months,
            total_freelance_months=resume.experience_metrics.total_freelance_months,
        )
        
        # Call LLM
        response = self._call_llm_with_timeout(prompt)
        
        # Parse and validate response
        return self._parse_response(response)
    
    def _is_valid_input(self, data: dict) -> bool:
        """Check if input has minimum required data"""
        personal = data.get('personal', {})
        
        # Must have at least a name
        if not personal.get('name'):
            return False
        
        # Should have at least one of: experience, education, skills
        has_content = (
            len(data.get('experience', [])) > 0 or
            len(data.get('education', [])) > 0 or
            len(data.get('skills', [])) > 0 or
            len(data.get('projects', [])) > 0
        )
        
        return has_content
    
    def _call_llm_with_timeout(self, prompt: str) -> str:
        """Call Ollama with timeout"""
        
        def _make_request():
            return self.client.chat(
                model=self.config.ollama_model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a resume classifier. Return only valid JSON. No markdown fences.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                format='json',
                options={
                    'temperature': self.config.temperature,
                    'num_predict': self.config.num_predict,
                    'num_ctx': self.config.num_ctx,
                }
            )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_make_request)
            
            try:
                result = future.result(timeout=self.config.request_timeout)
                return result['message']['content']
            except FuturesTimeoutError:
                raise TimeoutError(
                    f"Classification timed out after {self.config.request_timeout}s"
                )
    
    def _parse_response(self, response: str) -> ClassificationResult:
        """Parse LLM response to ClassificationResult"""
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON
            data = self._extract_json(response)
            if data is None:
                return self._error_result("Failed to parse classifier response")
        
        # Handle error response from LLM
        if 'error' in data:
            return ClassificationResult(
                classification=Classification(
                    experience_level=ExperienceLevel.FRESHER,
                    tech_domain="unknown",
                    confidence=0.0
                ),
                scoring=Scoring(),
                flags=[],
                domain_evidence=DomainEvidence(),
                summary="",
                error=data.get('error'),
                message=data.get('message')
            )
        
        # Parse classification
        try:
            classification_data = data.get('classification', {})
            classification = Classification(
                experience_level=self._parse_experience_level(
                    classification_data.get('experience_level', 'FRESHER')
                ),
                tech_domain=classification_data.get('tech_domain', 'unknown'),
                confidence=classification_data.get('confidence', 0.5)
            )
        except Exception as e:
            classification = Classification(
                experience_level=ExperienceLevel.FRESHER,
                tech_domain="unknown",
                confidence=0.0
            )
        
        # Parse scoring
        scoring_data = data.get('scoring', {})
        scoring = Scoring(
            fresher_score=scoring_data.get('fresher_score', 0),
            experienced_score=scoring_data.get('experienced_score', 0),
            deciding_factors=scoring_data.get('deciding_factors', [])
        )
        
        # Parse domain evidence
        evidence_data = data.get('domain_evidence', {})
        domain_evidence = DomainEvidence(
            primary_signals=evidence_data.get('primary_signals', []),
            conflicting_signals=evidence_data.get('conflicting_signals', [])
        )
        
        return ClassificationResult(
            classification=classification,
            scoring=scoring,
            flags=data.get('flags', []),
            domain_evidence=domain_evidence,
            summary=data.get('summary', '')
        )
    
    def _parse_experience_level(self, value: str) -> ExperienceLevel:
        """Parse experience level string to enum"""
        value = str(value).upper().strip()
        if value in ['EXPERIENCED', 'EXPERIENCE']:
            return ExperienceLevel.EXPERIENCED
        return ExperienceLevel.FRESHER
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from text"""
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except:
                return None
        return None
    
    def _error_result(self, message: str) -> ClassificationResult:
        """Create error result"""
        return ClassificationResult(
            classification=Classification(
                experience_level=ExperienceLevel.FRESHER,
                tech_domain="unknown",
                confidence=0.0
            ),
            scoring=Scoring(),
            flags=["parse_error"],
            domain_evidence=DomainEvidence(),
            summary="",
            error="parse_error",
            message=message
        )