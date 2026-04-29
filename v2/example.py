# Example 1: Using Resume Model
from models.resume import Resume

# Parse from JSON (e.g., from LLM output)
resume_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "skills": ["Python", "JavaScript", "React"],
    "experience": [
        {
            "company": "Google",
            "title": "Software Engineer",
            "type": "full-time",
            "start_date": "Jan 2022",
            "end_date": "Present",
            "duration_months": 35,
            "responsibilities": ["Built microservices", "Led team"]
        },
        {
            "company": "Amazon",
            "title": "Software Engineering Intern",
            "start_date": "May 2021",
            "end_date": "Aug 2021",
            "duration_months": 4,
            "responsibilities": ["Summer internship"]
        }
    ],
    "education": [
        {
            "institution": "Stanford University",
            "degree": "BS Computer Science",
            "graduation_year": 2021
        }
    ]
}

resume = Resume.model_validate(resume_data)

print(f"Name: {resume.name}")
print(f"Status: {resume.candidate_status}")  # EXPERIENCED
print(f"Total Experience: {resume.total_experience_years} years")
print(f"Skills: {resume.skills}")

# Get validation report
report = resume.get_validation_report()
print(f"Valid: {report['is_valid']}")

# Convert to classifier format
classifier_input = resume.to_classifier_format()


# Example 2: Using Classification Model
from models.classification import ClassificationResult, ExperienceLevel

classification_data = {
    "classification": {
        "experience_level": "EXPERIENCED",
        "tech_domain": "Full-Stack",
        "confidence": 0.85
    },
    "scoring": {
        "fresher_score": 15,
        "experienced_score": 85,
        "deciding_factors": ["3+ years at Google", "Senior title"]
    },
    "flags": [
        {
            "flag": "strong_projects",
            "reason": "Built open-source tool with 500+ stars",
            "severity": "low"
        },
        {
            "flag": "career_gap",
            "reason": "8-month gap in 2021",
            "severity": "medium"
        }
    ],
    "domain_evidence": {
        "primary_signals": ["React in skills", "Full-Stack title"],
        "conflicting_signals": []
    },
    "summary": "Experienced full-stack developer with strong project portfolio."
}

result = ClassificationResult.model_validate(classification_data)

print(f"Level: {result.experience_level.value}")
print(f"Domain: {result.tech_domain}")
print(f"Confidence: {result.confidence}")
print(f"Is Experienced: {result.is_experienced}")
print(f"Risk Score: {result.risk_score}")
print(f"Has Red Flags: {result.has_red_flags}")

# Check specific flags
for flag in result.flags:
    print(f"Flag: {flag.flag} | Type: {flag.flag_type.value} | Reason: {flag.reason}")