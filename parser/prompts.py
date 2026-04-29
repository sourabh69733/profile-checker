
RESUME_PARSE_EXPERIENCE = """
Extract job history, domains, and skills from the resume.

TASK:
1. ONLY extract jobs from the "Experience", "Employment", or "Work History" sections. 
2. IGNORE "Education", "Projects", "Leadership", or "Extracurricular" sections. Stop extracting jobs when you see a new section header (sections are usually separated by newlines/blank lines).
3. Identify the job type (e.g., "Full-time", "Part-time", "Contract", "Internship", "Freelance").
4. Extract exact start and end dates. They might be formatted as "Jan 2021", "01/2021", or just years like "2011".
5. Extract overall domains and skills from the resume.

| Type | Keywords to Identify | Examples |
|------|---------------------|----------|
| internship | "Intern", "Internship", "Trainee", "Apprentice", "Co-op", "Fellow", "Summer Intern" | "Software Engineering Intern", "Data Science Trainee" |
| contract | "Contract", "Contractor", "Consultant", "Consulting", "C2C", "W2", "via [Agency]", "Client:", "Staffing" | "Contract Developer", "Consultant at Deloitte", "via TCS" |
| freelance | "Freelance", "Self-employed", "Self employed", "Independent", "Own Business", "Upwork", "Fiverr" | "Freelance Web Developer", "Self-employed Consultant" |
| full-time | Default - regular jobs without any above keywords | "Software Engineer", "Product Manager", "Data Analyst" |

OUTPUT ONLY VALID JSON IN THIS EXACT FORMAT (Replace < > with extracted data):
{{
  "jobs":[
    {{
      "title": "<extract_job_title>",
      "company": "<extract_company_name>",
      "start_date": "<extract_start_date_or_month_year>",
      "end_date": "<extract_end_date_or_Present>",
      "job_type": "<extract_job_type>"
    }}
  ],
  "domains": ["<extract_domain_1>", "<extract_domain_2>"],
  "skills": ["<extract_skill_1>", "<extract_skill_2>"]
}}

RESUME:
---
{resume_text}
---
"""


RESUME_PARSE_PROMPT_SHORT = """
You are an expert resume parser. Extract ALL information from the resume with 100% accuracy.
Read the entire resume carefully before extracting. Do not skip any section.

================================================================================
SECTION 1: EXPERIENCE TYPE CLASSIFICATION
================================================================================

Classify each job based on keywords in the title and company name:

| Type | Keywords to Identify | Examples |
|------|---------------------|----------|
| internship | "Intern", "Internship", "Trainee", "Apprentice", "Co-op", "Fellow", "Summer Intern" | "Software Engineering Intern", "Data Science Trainee" |
| contract | "Contract", "Contractor", "Consultant", "Consulting", "C2C", "W2", "via [Agency]", "Client:", "Staffing" | "Contract Developer", "Consultant at Deloitte", "via TCS" |
| freelance | "Freelance", "Self-employed", "Self employed", "Independent", "Own Business", "Upwork", "Fiverr" | "Freelance Web Developer", "Self-employed Consultant" |
| part-time | "Part-time", "Part time", explicitly mentions reduced hours | "Part-time Developer" |
| full-time | Default - regular jobs without any above keywords | "Software Engineer", "Product Manager", "Data Analyst" |

CLASSIFICATION PRIORITY (check in this order):
1. If title contains "Intern" anywhere → internship (ALWAYS, even "Senior Intern")
2. If title/company contains "Contract" or "Consultant" → contract
3. If title/company contains "Freelance" or "Self-employed" → freelance
4. If title contains "Part-time" → part-time
5. Otherwise → full-time

================================================================================
SECTION 2: DURATION CALCULATION RULES
================================================================================

Calculate duration_months precisely using these rules:

MONTH MAPPING:
Jan=1, Feb=2, Mar=3, Apr=4, May=5, Jun=6, Jul=7, Aug=8, Sep=9, Oct=10, Nov=11, Dec=12

CURRENT DATE ASSUMPTION:
"Present", "Current", "Now", "Ongoing" = December 2024

CALCULATION FORMULA:
duration_months = (end_year - start_year) × 12 + (end_month - start_month) + 1

EXAMPLES:
| Start Date | End Date | Calculation | duration_months |
|------------|----------|-------------|-----------------|
| Jan 2022 | Dec 2023 | (2023-2022)×12 + (12-1) + 1 | 24 |
| Mar 2023 | Present | (2024-2023)×12 + (12-3) + 1 | 22 |
| Jun 2021 | Aug 2021 | (2021-2021)×12 + (8-6) + 1 | 3 |
| May 2019 | Aug 2019 | (2019-2019)×12 + (8-5) + 1 | 4 |
| 2020 | 2022 | Assume Jan to Dec, (2022-2020+1)×12 | 36 |
| Jan 2024 | Present | (2024-2024)×12 + (12-1) + 1 | 12 |

IF DATES ARE UNCLEAR:
- Only year given (e.g., "2020 - 2022") → Assume Jan to Dec
- Duration mentioned (e.g., "2 years") → Convert to months (24)
- Single date with no end → Assume 12 months if not "Present"

================================================================================
SECTION 3: EXTRACTION RULES BY SECTION
================================================================================

=== PERSONAL INFORMATION ===
- name: Full name (usually at top of resume)
- email: Must contain "@" symbol
- phone: Include country code if present
- location: City, State/Country format
- linkedin: Full URL or linkedin.com/in/username
- github: Full URL or github.com/username
- website: Personal website or portfolio URL

=== PROFESSIONAL SUMMARY ===
- Look for: "Summary", "Profile", "About", "Objective", "Professional Summary"
- Extract as single string (1-3 sentences)

=== SKILLS ===
- Extract as FLAT array: ["Python", "JavaScript", "AWS", "Docker", "SQL"]
- DO NOT use nested objects or categories
- Include skills from: Skills section, job descriptions, project descriptions
- Standardize names:
  * "JS" → "JavaScript"
  * "K8s" → "Kubernetes"
  * "Postgres" → "PostgreSQL"
  * "React.js" → "React"
  * "Node" → "Node.js"
- Exclude soft skills (communication, leadership, teamwork)
- Remove duplicates

=== EXPERIENCE (MOST CRITICAL - READ CAREFULLY) ===

RULE 1: Extract EVERY job as a SEPARATE entry
- Different company = new entry
- Same company but different title = new entry (promotion)
- Same company but different time period = new entry

RULE 2: DO NOT skip any job type
- Include ALL: full-time, internship, contract, freelance, part-time
- Contract and consulting jobs are often missed - look carefully!
- Short duration jobs (even 1-3 months) must be included

RULE 3: DO NOT create duplicate entries
- Same company + same title + same dates = ONE entry only
- If same job appears multiple times in resume, extract once

RULE 4: Extract complete information for each job
- company: Exact company name (include client if applicable: "TCS (Client: Microsoft)")
- title: Exact job title as written
- type: Classify using rules from Section 1
- location: Job location if mentioned
- start_date: Format as "Mon YYYY" (e.g., "Jan 2021")
- end_date: Format as "Mon YYYY" or "Present"
- duration_months: Calculate using rules from Section 2
- responsibilities: Array of bullet points/achievements

=== EDUCATION ===
- Extract ALL education entries (degrees, diplomas)
- institution: Full name (e.g., "Massachusetts Institute of Technology", not "MIT")
- degree: Full degree name (e.g., "Bachelor of Science in Computer Science")
- field: Just the major/specialization (e.g., "Computer Science")
- start_year: When started (e.g., "2018" or "Aug 2018")
- end_year: When ended or expected (e.g., "2022" or "Expected May 2025")
- graduation_year: Extract as integer (e.g., 2022)
- gpa: If mentioned (e.g., "3.8/4.0" or "3.8")

DEGREE ABBREVIATIONS TO EXPAND:
- B.S., BS, B.Sc. → Bachelor of Science
- B.A., BA → Bachelor of Arts
- B.E., B.Tech → Bachelor of Engineering/Technology
- M.S., MS → Master of Science
- M.Tech, ME → Master of Engineering
- MBA → Master of Business Administration
- Ph.D., PhD → Doctor of Philosophy

=== CERTIFICATIONS ===
- Separate from education
- name: Full certification name
- issuer: Organization (e.g., "AWS", "Google", "Microsoft", "Coursera")
- date: When obtained if mentioned

=== PROJECTS ===
- Personal projects, side projects, open source, hackathons
- name: Project name
- description: Brief description
- technologies: Array of technologies used
- url: GitHub link or live URL if mentioned

=== LANGUAGES ===
- Spoken/written languages (NOT programming languages)
- e.g., ["English", "Spanish", "Hindi", "Mandarin"]

================================================================================
SECTION 4: EXPERIENCE METRICS CALCULATION
================================================================================

After extracting all experiences, calculate totals:

total_full_time_months = SUM of duration_months where type = "full-time"
total_internship_months = SUM of duration_months where type = "internship"
total_contract_months = SUM of duration_months where type = "contract"
total_freelance_months = SUM of duration_months where type = "freelance"

VERIFICATION: The sum of all individual duration_months should equal:
total_full_time_months + total_internship_months + total_contract_months + total_freelance_months

================================================================================
SECTION 5: COMMON MISTAKES TO AVOID
================================================================================

❌ WRONG: Skipping contract or consulting jobs
✅ RIGHT: Extract ALL jobs including contract, consulting, freelance

❌ WRONG: Marking "Software Engineering Intern" as full-time
✅ RIGHT: Any title with "Intern" = internship

❌ WRONG: Creating duplicate entries for same job
✅ RIGHT: Each unique job appears exactly once

❌ WRONG: Skills as nested object {{"languages": ["Python"], "frameworks": ["React"]}}
✅ RIGHT: Skills as flat array ["Python", "React"]

❌ WRONG: duration_months = 0 when dates are available
✅ RIGHT: Always calculate duration from dates

❌ WRONG: Missing education when degree and institution exist
✅ RIGHT: Extract education even if graduation year is missing

❌ WRONG: experience_metrics doesn't match sum of individual durations
✅ RIGHT: Recalculate metrics after extracting all experiences

================================================================================
SECTION 6: RESUME TO PARSE
================================================================================

{resume_text}

================================================================================
SECTION 7: OUTPUT FORMAT
================================================================================

Return ONLY valid JSON. No markdown code blocks. No explanations.

{{
    "name": "string",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "linkedin": "string or null",
    "github": "string or null",
    "website": "string or null",
    "summary": "string or null",
    
    "skills": ["skill1", "skill2", "skill3"],
    
    "experience_metrics": {{
        "total_full_time_months": integer,
        "total_internship_months": integer,
        "total_contract_months": integer,
        "total_freelance_months": integer
    }},
    
    "experience": [
        {{
            "company": "string",
            "title": "string",
            "type": "full-time | internship | contract | freelance | part-time",
            "location": "string or null",
            "start_date": "string (e.g., 'Jan 2021')",
            "end_date": "string (e.g., 'Dec 2022' or 'Present')",
            "duration_months": integer,
            "responsibilities": ["string", "string"]
        }}
    ],
    
    "education": [
        {{
            "institution": "string",
            "degree": "string",
            "field": "string or null",
            "start_year": "string or null",
            "end_year": "string or null",
            "graduation_year": integer or null,
            "gpa": "string or null"
        }}
    ],
    
    "certifications": [
        {{
            "name": "string",
            "issuer": "string or null",
            "date": "string or null"
        }}
    ],
    
    "projects": [
        {{
            "name": "string",
            "description": "string or null",
            "technologies": ["string"],
            "url": "string or null"
        }}
    ],
    
    "languages": ["string"]
}}

================================================================================
SECTION 8: EXAMPLE (FOR REFERENCE)
================================================================================

EXAMPLE INPUT:
'''
Jane Smith | jane.smith@email.com | +1-555-123-4567 | San Francisco, CA
LinkedIn: linkedin.com/in/janesmith | GitHub: github.com/janesmith

Summary:
Full-stack developer with 4+ years of experience in web development.

Skills:
Python, JavaScript, React, Node.js, PostgreSQL, AWS, Docker, Kubernetes

Experience:

Senior Software Engineer
Google | San Francisco, CA | Jan 2022 - Present
- Led development of microservices architecture
- Mentored team of 3 junior developers

Software Developer (Contract)
Meta via Accenture | Remote | Mar 2020 - Dec 2021
- Built React components for News Feed
- Improved page load time by 40%

Software Engineering Intern
Amazon | Seattle, WA | May 2019 - Aug 2019
- Developed internal automation tools
- Participated in code reviews

Education:
Bachelor of Science in Computer Science
Stanford University | 2015 - 2019 | GPA: 3.8

Certifications:
- AWS Solutions Architect Associate | Amazon Web Services | 2021
- Google Cloud Professional | Google | 2022

Projects:
- TaskManager (github.com/janesmith/taskmanager): A productivity app built with React and Node.js
'''

EXAMPLE OUTPUT:
{{
    "name": "Jane Smith",
    "email": "jane.smith@email.com",
    "phone": "+1-555-123-4567",
    "location": "San Francisco, CA",
    "linkedin": "linkedin.com/in/janesmith",
    "github": "github.com/janesmith",
    "website": null,
    "summary": "Full-stack developer with 4+ years of experience in web development.",
    "skills": ["Python", "JavaScript", "React", "Node.js", "PostgreSQL", "AWS", "Docker", "Kubernetes"],
    "experience_metrics": {{
        "total_full_time_months": 35,
        "total_internship_months": 4,
        "total_contract_months": 22,
        "total_freelance_months": 0
    }},
    "experience": [
        {{
            "company": "Google",
            "title": "Senior Software Engineer",
            "type": "full-time",
            "location": "San Francisco, CA",
            "start_date": "Jan 2022",
            "end_date": "Present",
            "duration_months": 35,
            "responsibilities": [
                "Led development of microservices architecture",
                "Mentored team of 3 junior developers"
            ]
        }},
        {{
            "company": "Meta via Accenture",
            "title": "Software Developer (Contract)",
            "type": "contract",
            "location": "Remote",
            "start_date": "Mar 2020",
            "end_date": "Dec 2021",
            "duration_months": 22,
            "responsibilities": [
                "Built React components for News Feed",
                "Improved page load time by 40%"
            ]
        }},
        {{
            "company": "Amazon",
            "title": "Software Engineering Intern",
            "type": "internship",
            "location": "Seattle, WA",
            "start_date": "May 2019",
            "end_date": "Aug 2019",
            "duration_months": 4,
            "responsibilities": [
                "Developed internal automation tools",
                "Participated in code reviews"
            ]
        }}
    ],
    "education": [
        {{
            "institution": "Stanford University",
            "degree": "Bachelor of Science in Computer Science",
            "field": "Computer Science",
            "start_year": "2015",
            "end_year": "2019",
            "graduation_year": 2019,
            "gpa": "3.8"
        }}
    ],
    "certifications": [
        {{
            "name": "AWS Solutions Architect Associate",
            "issuer": "Amazon Web Services",
            "date": "2021"
        }},
        {{
            "name": "Google Cloud Professional",
            "issuer": "Google",
            "date": "2022"
        }}
    ],
    "projects": [
        {{
            "name": "TaskManager",
            "description": "A productivity app built with React and Node.js",
            "technologies": ["React", "Node.js"],
            "url": "github.com/janesmith/taskmanager"
        }}
    ],
    "languages": []
}}

Note how:
- Contract job at Meta via Accenture is correctly identified as "contract"
- Intern role at Amazon is correctly identified as "internship"
- Full-time at Google is correctly identified as "full-time"
- duration_months are calculated correctly
- experience_metrics sums match: 35 + 4 + 22 + 0 = 61 total months
- Skills are a flat array

================================================================================
NOW PARSE THE RESUME AND RETURN JSON ONLY:
================================================================================
"""

