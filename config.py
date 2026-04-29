# config.py
from pydantic import BaseModel
from typing import Optional

class ParserConfig(BaseModel):
    # Model settings
    ollama_model: str = "llama3.2:3b"  # Use smaller model
    ollama_host: str = "http://localhost:11434"
    temperature: float = 0.0
    
    # Timeout settings (in seconds)
    request_timeout: int = 60          # Max time for LLM response
    extraction_timeout: int = 30       # Max time for text extraction
    total_timeout: int = 120           # Max total processing time
    
    # Performance settings
    max_tokens: int = 2048             # Limit output tokens
    num_ctx: int = 4096                # Context window (lower = faster)
    num_predict: int = 2048            # Max prediction tokens
    
    # Processing settings
    max_text_length: int = 8000        # Truncate long resumes
    enable_cleaning: bool = True
    enable_validation: bool = True
    
    # Retry settings
    max_retries: int = 2
    retry_delay: float = 1.0
    
    
    # Extraction settings
    supported_formats: list[str] = [".pdf", ".doc", ".docx"]
    max_file_size_mb: int = 10
    
    # LibreOffice path (for DOC conversion)
    libreoffice_path: Optional[str] = None  # Auto-detect if None



config = ParserConfig()