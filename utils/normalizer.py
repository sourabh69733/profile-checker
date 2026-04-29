# utils/normalizer.py
import json
import ast
from typing import Any

class DataNormalizer:
    """Normalize LLM output before validation"""
    
    def normalize(self, data: dict) -> dict:
        """Normalize all fields"""
        data = self._normalize_skills(data)
        data = self._normalize_lists(data)
        data = self._normalize_strings(data)
        return data
    
    def _normalize_skills(self, data: dict) -> dict:
        """Normalize skills to flat list of strings"""
        skills = data.get('skills', [])
        
        if skills is None:
            data['skills'] = []
            return data
        
        # Convert string to list
        if isinstance(skills, str):
            skills = self._parse_string_to_list(skills)
        
        # Flatten complex structures
        if isinstance(skills, list):
            flat_skills = []
            for item in skills:
                if isinstance(item, str):
                    flat_skills.append(item)
                elif isinstance(item, dict):
                    flat_skills.extend(self._extract_skills_from_dict(item))
            data['skills'] = flat_skills
        
        return data
    
    def _extract_skills_from_dict(self, d: dict) -> list[str]:
        """Extract skill strings from dict"""
        skills = []
        
        # {"name": "Python"}
        if 'name' in d and isinstance(d['name'], str) and 'items' not in d:
            skills.append(d['name'])
        
        # {"skill": "Python"}
        if 'skill' in d:
            skills.append(str(d['skill']))
        
        # {"name": "Languages", "items": ["Python", "Java"]}
        if 'items' in d and isinstance(d['items'], list):
            for item in d['items']:
                if isinstance(item, str):
                    skills.append(item)
                elif isinstance(item, dict) and 'name' in item:
                    skills.append(str(item['name']))
        
        # {"category": "Backend", "skills": ["Python", "Java"]}
        if 'skills' in d and isinstance(d['skills'], list):
            for item in d['skills']:
                if isinstance(item, str):
                    skills.append(item)
        
        return skills
    
    def _parse_string_to_list(self, s: str) -> list:
        """Parse string that looks like a list"""
        # Try JSON
        try:
            return json.loads(s)
        except:
            pass
        
        # Try ast.literal_eval
        try:
            return ast.literal_eval(s)
        except:
            pass
        
        # Comma-separated
        if ',' in s:
            return [item.strip() for item in s.split(',') if item.strip()]
        
        return [s] if s.strip() else []
    
    def _normalize_lists(self, data: dict) -> dict:
        """Ensure list fields are lists"""
        list_fields = ['experience', 'education', 'certifications', 'projects', 'languages']
        
        for field in list_fields:
            if field in data:
                if data[field] is None:
                    data[field] = []
                elif isinstance(data[field], str):
                    data[field] = self._parse_string_to_list(data[field])
        
        return data
    
    def _normalize_strings(self, data: dict) -> dict:
        """Ensure string fields are strings or None"""
        string_fields = ['name', 'email', 'phone', 'location', 'linkedin', 'github', 'website', 'summary']
        
        for field in string_fields:
            if field in data:
                if data[field] is None:
                    continue
                if isinstance(data[field], list):
                    data[field] = ', '.join(str(item) for item in data[field])
                else:
                    data[field] = str(data[field]) if data[field] else None
        
        return data