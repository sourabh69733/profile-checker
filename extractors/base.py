# extractors/base.py
from abc import ABC, abstractmethod
from typing import Optional
import os

class BaseExtractor(ABC):
    """Base class for all format extractors"""
    
    supported_extensions: list[str] = []
    
    def can_handle(self, file_path: str) -> bool:
        """Check if this extractor can handle the file"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions
    
    @abstractmethod
    def extract(self, file_path: str) -> str:
        """Extract text from file"""
        pass
    
    def validate_file(self, file_path: str) -> None:
        """Validate file exists and is readable"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read file: {file_path}")