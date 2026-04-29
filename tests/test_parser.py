# tests/test_parser.py
import pytest
from main import ResumeParsingAgent
from config import ParserConfig

@pytest.fixture
def agent():
    return ResumeParsingAgent()

def test_pdf_parsing(agent, tmp_path):
    # Create a simple test PDF or use existing one
    result = agent.parse("tests/samples/sample.pdf")
    assert result.name is not None
    assert result.parse_confidence > 0

def test_unsupported_format(agent):
    with pytest.raises(ValueError, match="Unsupported format"):
        agent.parse("resume.txt")

def test_file_not_found(agent):
    with pytest.raises(FileNotFoundError):
        agent.parse("nonexistent.pdf")