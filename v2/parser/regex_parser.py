"""
Regex-based extraction for specific fields.
Used as backup and to enhance LLM extraction.
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dateutil import parser as date_parser


class RegexParser:
    """Extract specific fields using regex patterns."""
    
    # Date patterns
    DATE_PATTERNS = [
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\.?\s*(\d{4})',
        r'(\d{1,2})/(\d{4})',
        r'(\d{4})\s*[-–—]\s*(\d{4}|[Pp]resent|[Cc]urrent)',
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\s*[-–—]\s*(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|[Pp]resent|[Cc]urrent)\s*\.?\s*(\d{4})?',
    ]
    
    # Experience type keywords
    INTERNSHIP_KEYWORDS = ['intern', 'internship', 'trainee', 'apprentice', 'co-op', 'coop', 'fellow']
    CONTRACT_KEYWORDS = ['contract', 'contractor', 'consultant', 'consulting', 'c2c', 'w2', 'via ', 'client:', 'staffing']
    FREELANCE_KEYWORDS = ['freelance', 'freelancer', 'self-employed', 'self employed', 'independent', 'own business']
    
    # Skill extraction patterns
    SKILL_SECTION_PATTERN = r'(?i)(?:skills?|technologies?|tech\s+stack|competenc(?:ies|e)|expertise)[\s:]*(.+?)(?=\n\n|\n[A-Z]|\Z)'
    SKILL_LIST_PATTERN = r'(?:[•\-\*]\s*)?([A-Za-z][A-Za-z0-9\.\+\#\-\/\s]{1,30})(?:,|\n|$)'
    
    # Common skills to look for
    KNOWN_SKILLS = [
        # Languages
        'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Golang', 'Rust', 'Ruby', 'PHP', 
        'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Bash', 'Shell', 'SQL', 'HTML', 'CSS',
        # Frameworks
        'React', 'Angular', 'Vue', 'Vue.js', 'Node.js', 'Express', 'Django', 'Flask', 'FastAPI',
        'Spring', 'Spring Boot', '.NET', 'ASP.NET', 'Rails', 'Ruby on Rails', 'Laravel', 'Next.js',
        'Nuxt', 'Svelte', 'jQuery', 'Bootstrap', 'Tailwind', 'Material UI',
        # Databases
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'SQLite', 'Oracle', 'SQL Server',
        'DynamoDB', 'Cassandra', 'Neo4j', 'Firebase',
        # Cloud & DevOps
        'AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker', 'Kubernetes', 'K8s', 'Jenkins', 'GitLab CI',
        'GitHub Actions', 'Terraform', 'Ansible', 'CircleCI', 'Travis CI',
        # Tools
        'Git', 'GitHub', 'GitLab', 'Bitbucket', 'Jira', 'Confluence', 'Slack', 'VS Code', 'IntelliJ',
        'Postman', 'Swagger', 'Figma', 'Sketch',
        # Data & ML
        'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy', 'Spark', 'Hadoop',
        'Tableau', 'Power BI', 'Jupyter', 'Apache Kafka',
        # Mobile
        'React Native', 'Flutter', 'iOS', 'Android', 'SwiftUI', 'Jetpack Compose',
        # Other
        'REST', 'RESTful', 'GraphQL', 'gRPC', 'Microservices', 'Agile', 'Scrum', 'CI/CD',
        'Linux', 'Unix', 'Windows', 'macOS',
    ]
    
    def __init__(self):
        self.skills_pattern = self._build_skills_pattern()
    
    def _build_skills_pattern(self) -> re.Pattern:
        """Build regex pattern for known skills."""
        escaped_skills = [re.escape(skill) for skill in self.KNOWN_SKILLS]
        pattern = r'\b(' + '|'.join(escaped_skills) + r')\b'
        return re.compile(pattern, re.IGNORECASE)
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information."""
        header = text[:1000]  # Contact info usually in first 1000 chars
        
        result = {
            'name': self._extract_name(header),
            'email': self._extract_email(header),
            'phone': self._extract_phone(header),
            'linkedin': self._extract_linkedin(header),
            'github': self._extract_github(header),
            'location': self._extract_location(header),
        }
        
        return result
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name (usually first line or prominent text)."""
        lines = text.strip().split('\n')
        
        for line in lines[:5]:
            line = line.strip()
            # Skip if looks like contact info
            if '@' in line or re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                continue
            if 'linkedin' in line.lower() or 'github' in line.lower():
                continue
            # Check if looks like a name (2-4 words, mostly alpha)
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(word[0].isupper() and word.replace('-', '').replace("'", '').isalpha() for word in words):
                    return line
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        return match.group(0).lower() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number."""
        patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\+[0-9]{1,3}[-.\s]?[0-9]{10,12}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_linkedin(self, text: str) -> Optional[str]:
        """Extract LinkedIn URL or username."""
        patterns = [
            r'linkedin\.com/in/([a-zA-Z0-9_-]+)',
            r'linkedin:\s*([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"linkedin.com/in/{match.group(1)}"
        
        return None
    
    def _extract_github(self, text: str) -> Optional[str]:
        """Extract GitHub URL or username."""
        patterns = [
            r'github\.com/([a-zA-Z0-9_-]+)',
            r'github:\s*([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"github.com/{match.group(1)}"
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location."""
        # Common patterns
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})',  # City, ST
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+)',  # City, Country
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{match.group(1)}, {match.group(2)}"
        
        return None
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text."""
        found_skills = set()
        
        # Method 1: Find known skills anywhere in text
        matches = self.skills_pattern.findall(text)
        for match in matches:
            # Normalize skill name
            skill = self._normalize_skill(match)
            if skill:
                found_skills.add(skill)
        
        # Method 2: Look in skills section specifically
        skill_section_match = re.search(self.SKILL_SECTION_PATTERN, text, re.DOTALL)
        if skill_section_match:
            section_text = skill_section_match.group(1)
            # Extract comma/bullet separated items
            items = re.split(r'[,•\-\*\n|]', section_text)
            for item in items:
                item = item.strip()
                if 2 <= len(item) <= 30 and item[0].isalpha():
                    skill = self._normalize_skill(item)
                    if skill:
                        found_skills.add(skill)
        
        return sorted(list(found_skills))
    
    def _normalize_skill(self, skill: str) -> Optional[str]:
        """Normalize skill name."""
        skill = skill.strip()
        
        # Skip if too short or too long
        if len(skill) < 2 or len(skill) > 30:
            return None
        
        # Normalization mapping
        normalizations = {
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
        }
        
        skill_lower = skill.lower()
        if skill_lower in normalizations:
            return normalizations[skill_lower]
        
        # Check if it's a known skill (case-insensitive)
        for known_skill in self.KNOWN_SKILLS:
            if skill_lower == known_skill.lower():
                return known_skill
        
        # Return original if it looks valid
        if skill[0].isupper() or skill.isupper():
            return skill
        
        return skill.title() if skill.isalpha() else skill
    
    def extract_dates(self, text: str) -> List[Tuple[str, str]]:
        """Extract date ranges from text."""
        date_ranges = []
        
        # Pattern: "Month Year - Month Year" or "Month Year - Present"
        pattern = r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\.?\s*\d{4})\s*[-–—]\s*((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\.?\s*\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)'
        
        matches = re.findall(pattern, text)
        for start, end in matches:
            date_ranges.append((start.strip(), end.strip()))
        
        # Pattern: "Year - Year"
        pattern2 = r'(\d{4})\s*[-–—]\s*(\d{4}|[Pp]resent|[Cc]urrent)'
        matches2 = re.findall(pattern2, text)
        for start, end in matches2:
            # Avoid duplicates
            if not any(start in dr[0] for dr in date_ranges):
                date_ranges.append((start, end))
        
        return date_ranges
    
    def detect_experience_type(self, title: str, company: str = "") -> str:
        """Detect experience type from title and company."""
        combined = f"{title} {company}".lower()
        
        # Check internship first
        if any(kw in combined for kw in self.INTERNSHIP_KEYWORDS):
            return "internship"
        
        # Check contract
        if any(kw in combined for kw in self.CONTRACT_KEYWORDS):
            return "contract"
        
        # Check freelance
        if any(kw in combined for kw in self.FREELANCE_KEYWORDS):
            return "freelance"
        
        return "full-time"
    
    def calculate_duration_months(self, start_date: str, end_date: str) -> int:
        """Calculate duration in months between two dates."""
        try:
            # Parse start date
            start = self._parse_date(start_date)
            if not start:
                return 0
            
            # Parse end date
            if end_date.lower() in ['present', 'current', 'now', 'ongoing']:
                end = datetime.now()
            else:
                end = self._parse_date(end_date)
                if not end:
                    return 0
            
            # Calculate months
            months = (end.year - start.year) * 12 + (end.month - start.month) + 1
            return max(1, months)
        
        except Exception:
            return 0
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        date_str = date_str.strip()
        
        # Try common formats
        formats = [
            '%b %Y', '%B %Y', '%m/%Y', '%Y-%m', '%Y',
            '%b. %Y', '%B. %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try dateutil as fallback
        try:
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            return None