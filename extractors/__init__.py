# extractors/__init__.py
import os
from typing import Optional
from .base import BaseExtractor
from .pdf_extractor import PDFExtractor
from .word_extractor import WordExtractor

class ExtractorFactory:
    """Factory to get appropriate extractor for a file"""
    
    ALLOWED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    
    def __init__(self, libreoffice_path: Optional[str] = None):
        self.extractors = [
            PDFExtractor(),
            WordExtractor(libreoffice_path=libreoffice_path),
        ]
    
    def get_extractor(self, file_path: str) -> BaseExtractor:
        """Get appropriate extractor for file"""
        # Simple extension-based validation (no libmagic needed)
        self._validate_file_type(file_path)
        
        for extractor in self.extractors:
            if extractor.can_handle(file_path):
                return extractor
        
        ext = os.path.splitext(file_path)[1].lower()
        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported formats: PDF, DOC, DOCX"
        )
    
    def extract(self, file_path: str) -> str:
        """Extract text from file using appropriate extractor"""
        extractor = self.get_extractor(file_path)
        return extractor.extract(file_path)
    
    def _validate_file_type(self, file_path: str) -> None:
        """Validate file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file type: {ext}. "
                f"Please upload a PDF or Word document (.pdf, .doc, .docx)"
            )
        
        # Basic file header check (optional, no libmagic)
        self._check_file_header(file_path, ext)
    
    def _check_file_header(self, file_path: str, ext: str) -> None:
        """Basic file header validation without libmagic"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
            
            # PDF check
            if ext == '.pdf' and not header.startswith(b'%PDF'):
                raise ValueError("File does not appear to be a valid PDF")
            
            # DOCX check (ZIP-based format)
            if ext == '.docx' and not header.startswith(b'PK'):
                raise ValueError("File does not appear to be a valid DOCX")
            
            # DOC check (OLE format)
            if ext == '.doc' and not header.startswith(b'\xd0\xcf\x11\xe0'):
                # Could also be DOCX renamed to DOC
                if header.startswith(b'PK'):
                    pass  # Allow it, will be handled
                else:
                    raise ValueError("File does not appear to be a valid DOC")
                    
        except IOError as e:
            raise ValueError(f"Cannot read file: {e}")