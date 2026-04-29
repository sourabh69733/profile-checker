# parser/llm_parser.py
import json
import ollama
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pydantic import ValidationError

from .prompts import RESUME_PARSE_PROMPT_SHORT, RESUME_PARSE_EXPERIENCE
from models.resume import Resume
from utils.normalizer import DataNormalizer
from config import ParserConfig
from dateutil import parser

class TimeoutError(Exception):
    """Custom timeout error"""
    pass

def parse_date(date_str: str) -> datetime:
    """Safely converts resume date strings to Python datetime objects."""
    if not date_str:
        return None
        
    date_str_lower = str(date_str).lower().strip()
    if date_str_lower in ['present', 'current', 'now', 'till date']:
        return datetime.now()
        
    try:
        # Default to January 1st so year-only dates (e.g. "2011") calculate correctly
        default_date = datetime(2000, 1, 1)
        return parser.parse(date_str, fuzzy=True, default=default_date)
    except (ValueError, TypeError):
        return None

def calculate_experience(data: dict) -> dict:
    """Calculates total years/months and determines Fresher vs Experienced."""
    
    intervals = []
    counted_jobs =[]

    # 1. Parse dates and skip internships
    for job in data.get('jobs',[]):
        job_type = str(job.get('job_type', '')).lower()
        
        # Explicitly skip internships/volunteering
        if 'intern' in job_type or 'volunteer' in job_type or 'student' in job_type:
            continue
            
        start = parse_date(job.get('start_date'))
        end = parse_date(job.get('end_date'))
        
        if start and end:
            # Fix backward dates if the resume had a typo
            if start > end:
                start, end = end, start
                
            intervals.append([start, end])
            counted_jobs.append(job) # Keep track of which jobs were actually counted

    # 2. Merge overlapping jobs
    total_months = 0
    if intervals:
        # Sort by start date
        intervals.sort(key=lambda x: x[0])
        
        merged = [intervals[0]]
        for current in intervals[1:]:
            previous = merged[-1]
            # Merge if the dates overlap
            if current[0] <= previous[1]:
                previous[1] = max(previous[1], current[1])
            else:
                merged.append(current)
                
        # 3. Calculate exact months from the merged blocks
        for start, end in merged:
            months_diff = (end.year - start.year) * 12 + (end.month - start.month)
            total_months += months_diff

    # 4. Convert to Years
    total_years = round(total_months / 12.0, 1)

    # 5. Determine Experience Level 
    # (You can change this logic. E.g., if you only want people with > 6 months to be "Experienced")
    if total_months > 0:
        experience_level = "Experienced"
    else:
        experience_level = "Fresher"

    # Return the beautifully formatted final data
    return {
        "candidate_status": experience_level,
        "total_experience_years": total_years,
        "total_experience_months": total_months,
        "domains": data.get('domains',[]),
        "skills": data.get('skills',[]),
        "valid_jobs_counted": counted_jobs
    }
    
class LLMParser:
    """Parse resume text using Ollama LLM"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.client = ollama.Client(host=config.ollama_host)
        self.normalizer = DataNormalizer()
    
    def parse_v2(self, text: str):
        # Truncate text if too long
        text = self._truncate_text(text)
        current_date = datetime.now().strftime("%B %Y")
        
        # Generate prompt
        prompt = RESUME_PARSE_EXPERIENCE.format(resume_text=text, current_date = current_date)
        
        # Call LLM with timeout
        response = self._call_llm_with_timeout(prompt)
        
        # Parse JSON response
        parsed_data = self._parse_json(response)
        
        # Normalize data before validation
        parsed_data = self.normalizer.normalize(parsed_data)
        
        # Add metadata
        parsed_data['raw_text'] = text
        parsed_data['parsed_at'] = datetime.now()
        
        return calculate_experience(parsed_data)
        
    def parse(self, text: str) -> Resume:
        """Parse resume text with timeout"""
        
        # Truncate text if too long
        text = self._truncate_text(text)
        
        # Generate prompt
        prompt = RESUME_PARSE_PROMPT_SHORT.format(resume_text=text)
        
        # Call LLM with timeout
        response = self._call_llm_with_timeout(prompt)
        
        # Parse JSON response
        parsed_data = self._parse_json(response)
        
        # Normalize data before validation
        parsed_data = self.normalizer.normalize(parsed_data)
        
        # Add metadata
        parsed_data['raw_text'] = text
        parsed_data['parsed_at'] = datetime.now()
        
        return self._validate_response(parsed_data)
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to max length"""
        if len(text) > self.config.max_text_length:
            print(f"⚠️ Truncating text from {len(text)} to {self.config.max_text_length} chars")
            return text[:self.config.max_text_length]
        return text
    
    def _call_llm_with_timeout(self, prompt: str) -> str:
        """Call Ollama with timeout"""
        
        def _make_request():
            return self.client.chat(
                model=self.config.ollama_model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a resume parser. Return only valid JSON with simple data types. Skills should be a flat list of strings like ["Python", "Java"].'
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
                    f"LLM request timed out after {self.config.request_timeout} seconds."
                )
    
    def _parse_json(self, response: str) -> dict:
        """Parse JSON from LLM response"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            json_match = self._extract_json(response)
            if json_match:
                return json.loads(json_match)
            raise ValueError("Failed to parse JSON from LLM response")
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text"""
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end + 1]
        return None
    
    def _validate_response(self, data: dict) -> Resume:
        """Validate parsed data"""
        try:
            return Resume(**data)
        except ValidationError as e:
            print(f"⚠️ Validation error: {e}")
            data = self._fix_validation_errors(data, e)
            return Resume(**data)
    
    def _fix_validation_errors(self, data: dict, error: ValidationError) -> dict:
        """Fix validation errors"""
        for err in error.errors():
            field = err['loc'][0] if err['loc'] else None
            
            if field and field in data:
                error_type = err['type']
                
                if error_type == 'list_type':
                    # Convert to empty list
                    data[field] = []
                elif error_type == 'string_type':
                    data[field] = str(data[field]) if data[field] else None
                else:
                    # Set to None/empty as fallback
                    data[field] = None if 'str' in str(err) else []
        
        return data