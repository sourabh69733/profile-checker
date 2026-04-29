# extractors/pdf_extractor.py
import pdfplumber
from .base import BaseExtractor

class PDFExtractor(BaseExtractor):
    """Extract text from PDF files"""
    
    supported_extensions = ['.pdf']
    
    def extract(self, file_path: str) -> str:
        self.validate_file(file_path)
        
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract regular text
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    table_text = self._table_to_text(table)
                    if table_text:
                        text_parts.append(table_text)
        
        return "\n\n".join(text_parts)
    
    def _table_to_text(self, table: list) -> str:
        """Convert table data to readable text"""
        if not table:
            return ""
        
        rows = []
        for row in table:
            # Filter None values and join cells
            cells = [str(cell) if cell else "" for cell in row]
            rows.append(" | ".join(cells))
        
        return "\n".join(rows)