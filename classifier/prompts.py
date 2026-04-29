CLASSIFICATION_PROMPT = """
You are an expert HR analyst. Analyze the parsed resume data and provide a detailed classification.

CLASSIFICATION RULES:

EXPERIENCE LEVEL:
- FRESHER: Less than 12 months of FULL-TIME work experience (internships do NOT count as full-time)
- EXPERIENCED: 12 or more months of FULL-TIME work experience
- Contract and freelance work DOES count toward experience

TECH DOMAIN DETECTION:
Identify the PRIMARY tech domain based on skills, job titles, and project technologies.
Common domains: "Frontend", "Backend", "Full-Stack", "Mobile", "DevOps", "Data Science", 
"Machine Learning", "Cloud", "Cybersecurity", "QA/Testing", "Embedded Systems", 
"Blockchain", "Game Development", "UI/UX", "Database", "Networking", "Unknown"

SCORING GUIDELINES:
- fresher_score (0-100): How strongly the resume indicates a fresher profile
- experienced_score (0-100): How strongly the resume indicates an experienced profile
- These scores should NOT necessarily sum to 100 (a confusing resume might score 50/50)

FLAGS TO DETECT (with reason for each):
For each applicable flag, provide a specific reason from the resume.

| Flag | When to Apply |
|------|---------------|
| career_gap | Gap of 6+ months between roles |
| career_switch | Changed tech domain significantly between roles |
| overqualified | Senior person with 5+ years applying, or senior titles |
| underqualified | Missing key skills for claimed experience level |
| frequent_job_changes | 3+ jobs in 2 years |
| no_formal_education | Missing degree/institution information |
| strong_projects | Notable personal/open-source projects with impact |
| certification_heavy | 3+ relevant technical certifications |
| internship_only | Only internship experience, no full-time roles |
| leadership_experience | Team lead/manager/director titles or responsibilities |
| startup_experience | Worked at startups (small team, seed/series funding mentioned) |
| faang_experience | Worked at FAANG/MAANG or top tech companies |
| remote_work | Remote work experience indicated |
| freelancer | Primarily freelance/contract background |
| recent_graduate | Graduated within last 12 months |
| skill_mismatch | Skills don't align with job titles or experience |

PARSED RESUME DATA:
{parsed_resume}

EXPERIENCE METRICS FROM PARSER:
- Total Full-Time Months: {total_full_time_months}
- Total Internship Months: {total_internship_months}
- Total Contract Months: {total_contract_months}
- Total Freelance Months: {total_freelance_months}

ANALYSIS INSTRUCTIONS:
1. First, verify the experience metrics above against the experience list
2. Determine experience_level based on full-time months (>=12 = EXPERIENCED)
3. Identify the primary tech domain from skills and job titles
4. Calculate fresher_score and experienced_score independently
5. For EACH applicable flag, provide a specific reason from the resume
6. Find primary signals that support your domain classification
7. Note any conflicting signals (e.g., frontend title but mostly backend skills)
8. Write a one-sentence summary

RESPOND WITH THIS EXACT JSON STRUCTURE:
{{
  "classification": {{
    "experience_level": "FRESHER or EXPERIENCED",
    "tech_domain": "string",
    "confidence": 0.0 to 1.0
  }},
  "scoring": {{
    "fresher_score": 0 to 100,
    "experienced_score": 0 to 100,
    "deciding_factors": ["list", "of", "key", "factors"]
  }},
  "flags": [
    {{
      "flag": "flag_name",
      "reason": "Specific evidence from resume for this flag",
      "severity": "low or medium or high"
    }}
  ],
  "domain_evidence": {{
    "primary_signals": ["evidence", "supporting", "domain"],
    "conflicting_signals": ["any", "contradicting", "evidence"]
  }},
  "summary": "One sentence plain-English verdict about this candidate."
}}

JSON only, no markdown, no explanation:
"""