# example_usage.py
from main import ResumeParsingAgent, parse_resume
from config import ParserConfig
import time
from models.resume import Resume
import json

# Basic usage

file_path = "sample_resumes/sourabh.pdf"


# print(f"Name: {pdf_resume.name}")
# print(f"Email: {pdf_resume.email}")
# print(f"Skills: {', '.join(pdf_resume.skills)}")

# With custom config
config = ParserConfig(
    # ollama_model="gpt-oss:20b",
    
    # ollama_model="phi3:3.8b",
    ollama_model="llama3.2:3b",
    # ollama_model="qwen3.5:latest",  # Use larger model
    temperature=0.0,
    enable_validation=True
)

agent = ResumeParsingAgent(config=config)


# result = agent.parse_and_classify(file_path)
# print(f"Name: {result['resume']['name']}")
# print(f"Experience Level: {result['classification']['classification']['experience_level']}")
# print(f"Tech Domain: {result['classification']['classification']['tech_domain']}")
# print(f"Confidence: {result['classification']['classification']['confidence']}")
# print(f"Summary: {result['classification']['summary']}")

resume = agent.get_resume_experience(file_path)
# print(f"Parsed: {resume.name}")
# print(f"Skills: {resume.skills}")
# print(f"experience_metrics: {resume.experience_metrics}")
# print(f"Education: {resume.education}")
# print(f"Experience: {len(resume.experience)} jobs")

# print(resume.model_dump_json(indent=4))
resume["raw_text"] = ""
print(resume)

# with open("resume.txt", "w") as f:
#     f.write(resume.model_dump_json())

# resume = json.loads(open("resume.txt", "r").read())

# resume = Resume(**resume)

# resume = Resume(name='Sourabh Sahu', email='sourabhsahu69733@gmail.com', phone='+91 9358337807', location=None, linkedin=None, github=None, website=None, summary='Experienced Software Developer specialized in Distributed Backend systems, skilled in efficiently building and managing production systems.', skills=['JavaScript', 'TypeScript', 'Python', 'Rust', 'C', 'HTML'])
# resume = Resume(**{ "name": "sourabh", "skills": [], "experience": [] })
# classification = agent.classify(resume)
# print(f"Level: {classification.classification.experience_level.value}")
# print(f"Domain: {classification.classification.tech_domain}")
# print(f"Fresher Score: {classification.scoring.fresher_score}")
# print(f"Experienced Score: {classification.scoring.experienced_score}")
# print(classification.model_dump_json(indent=4))

# # Parse different formats
# # pdf_resume = agent.parse("candidate.pdf")
# # docx_resume = agent.parse("candidate.docx")
# # doc_resume = agent.parse("candidate.doc")

# # Get as JSON
# json_output = agent.parse_to_json(file_path)
# print(json_output)

# # # Get as dictionary
# # dict_output = agent.parse_to_dict(file_path)

# # Access specific fields
# # for exp in pdf_resume.experience:
# #     print(f"{exp.title} at {exp.company}")

# # for edu in pdf_resume.education:
# #     print(f"{edu.degree} from {edu.institution}")