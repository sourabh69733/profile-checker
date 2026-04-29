"""
LLM-based resume parsing using Ollama.
"""
import json
import re
from typing import Optional, Dict, Any
import requests

from parser.prompts import RESUME_PARSE_PROMPT


class LLMParser:
    """Parse resume using LLM (Ollama)."""
    
    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        timeout: int = 120
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout
    
    def parse(self, resume_text: str) -> Dict[str, Any]:
        """
        Parse resume text using LLM.
        
        Returns:
            Parsed resume as dictionary
        """
        # Format prompt
        prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse JSON response
        parsed = self._parse_json_response(response)
        
        return parsed
    
    def _call_llm(self, prompt: str) -> str:
        """Call Ollama API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": 0.9,
                        "num_predict": 4096,
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"LLM request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Clean response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```"):
            # Find the JSON content
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                response = match.group(1).strip()
            else:
                # Remove first and last lines
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
        
        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            response = json_match.group(0)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            fixed = self._fix_json(response)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                return {"_parse_error": str(e), "_raw_response": response[:500]}
    
    def _fix_json(self, json_str: str) -> str:
        """Try to fix common JSON issues."""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix unquoted keys
        json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)
        
        # Fix single quotes
        json_str = json_str.replace("'", '"')
        
        return json_str


class LLMParserWithRetry(LLMParser):
    """LLM Parser with retry logic."""
    
    def __init__(self, max_retries: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.max_retries = max_retries
    
    def parse(self, resume_text: str) -> Dict[str, Any]:
        """Parse with retry on failure."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = super().parse(resume_text)
                
                # Check if parsing was successful
                if "_parse_error" not in result:
                    return result
                
                last_error = result.get("_parse_error")
                
            except Exception as e:
                last_error = str(e)
        
        # Return error result
        return {
            "_parse_error": last_error,
            "_attempts": self.max_retries + 1,
        }