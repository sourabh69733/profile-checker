# main.py
import os
import json
import time
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from config import ParserConfig, config
from extractors import ExtractorFactory
from parser.llm_parser import LLMParser, TimeoutError
from classifier.resume_classifier import ResumeClassifier
from utils.cleaner import TextCleaner
from utils.normalizer import DataNormalizer
from utils.validator import ResumeValidator
from models.resume import Resume
from models.classification import ClassificationResult

class ResumeParsingAgent:
    """Main agent for parsing and classifying resumes"""
    
    def __init__(self, config: ParserConfig = config):
        self.config = config
        self.extractor_factory = ExtractorFactory(
            libreoffice_path=config.libreoffice_path
        )
        self.cleaner = TextCleaner()
        self.parser = LLMParser(config)
        self.classifier = ResumeClassifier(config)
        self.validator = ResumeValidator()
    
    def get_resume_experience(self, file_path: str):
        """Parse resume file to structured data"""
        start_time = time.time()
        
        def _do_parse():
            self._validate_file(file_path)
            
            # Extract
            self._check_timeout(start_time, "extraction")
            print(f"📄 Extracting: {os.path.basename(file_path)}")
            raw_text = self._extract_with_timeout(file_path)
            
            if not raw_text or len(raw_text.strip()) < 50:
                raise ValueError("Could not extract sufficient text")
            
            print(f"📝 Extracted {len(raw_text)} characters")
            
            # Clean
            self._check_timeout(start_time, "cleaning")
            if self.config.enable_cleaning:
                print("🧹 Cleaning...")
                cleaned_text = self.cleaner.clean(raw_text)
            else:
                cleaned_text = raw_text
            
            # Parse
            self._check_timeout(start_time, "parsing")
            print(f"🤖 Parsing with {self.config.ollama_model}...")
            resume = self.parser.parse_v2(cleaned_text)
            
            # Validate
            self._check_timeout(start_time, "validation")
            # if self.config.enable_validation:
            #     print("✅ Validating...")
            #     resume = self.validator.validate(resume)
            
            # print(f"✨ Parsed! Confidence: {resume.parse_confidence}")
            return resume
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_parse)
            
            try:
                result = future.result(timeout=self.config.total_timeout)
                elapsed = time.time() - start_time
                print(f"⏱️ Parsing time: {elapsed:.2f}s")
                return result
            except FuturesTimeoutError:
                raise TimeoutError(
                    f"Parsing timed out after {self.config.total_timeout}s"
                )
        
    def parse(self, file_path: str) -> Resume:
        """Parse resume file to structured data"""
        start_time = time.time()
        
        def _do_parse():
            return self._parse_internal(file_path, start_time)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_parse)
            
            try:
                result = future.result(timeout=self.config.total_timeout)
                elapsed = time.time() - start_time
                print(f"⏱️ Parsing time: {elapsed:.2f}s")
                return result
            except FuturesTimeoutError:
                raise TimeoutError(
                    f"Parsing timed out after {self.config.total_timeout}s"
                )
    
    def classify(self, resume: Resume) -> ClassificationResult:
        """Classify a parsed resume"""
        start_time = time.time()
        
        print(resume.name)
        print(f"🔍 Classifying resume for: {resume.name}")
        result = self.classifier.classify(resume)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Classification time: {elapsed:.2f}s")
        print(f"📊 Result: {result.classification.experience_level.value} | {result.classification.tech_domain}")
        
        return result
    
    def parse_and_classify(self, file_path: str) -> dict:
        """Full pipeline: parse + classify"""
        start_time = time.time()
        
        # Step 1: Parse
        resume = self.parse(file_path)
        
        # Step 2: Classify
        classification = self.classify(resume)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Total pipeline time: {elapsed:.2f}s")
        
        return {
            "resume": resume.model_dump(exclude={'raw_text'}),
            "classification": classification.model_dump()
        }
    
    def _parse_internal(self, file_path: str, start_time: float) -> Resume:
        """Internal parsing logic"""
        
        self._validate_file(file_path)
        
        # Extract
        self._check_timeout(start_time, "extraction")
        print(f"📄 Extracting: {os.path.basename(file_path)}")
        raw_text = self._extract_with_timeout(file_path)
        
        if not raw_text or len(raw_text.strip()) < 50:
            raise ValueError("Could not extract sufficient text")
        
        print(f"📝 Extracted {len(raw_text)} characters")
        
        # Clean
        self._check_timeout(start_time, "cleaning")
        if self.config.enable_cleaning:
            print("🧹 Cleaning...")
            cleaned_text = self.cleaner.clean(raw_text)
        else:
            cleaned_text = raw_text
        
        # Parse
        self._check_timeout(start_time, "parsing")
        print(f"🤖 Parsing with {self.config.ollama_model}...")
        resume = self.parser.parse(cleaned_text)
        
        # Validate
        self._check_timeout(start_time, "validation")
        if self.config.enable_validation:
            print("✅ Validating...")
            resume = self.validator.validate(resume)
        
        print(f"✨ Parsed! Confidence: {resume.parse_confidence}")
        return resume
    
    def _extract_with_timeout(self, file_path: str) -> str:
        """Extract with timeout"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.extractor_factory.extract, file_path)
            try:
                return future.result(timeout=self.config.extraction_timeout)
            except FuturesTimeoutError:
                raise TimeoutError(f"Extraction timed out")
    
    def _check_timeout(self, start_time: float, stage: str) -> None:
        """Check timeout"""
        elapsed = time.time() - start_time
        remaining = self.config.total_timeout - elapsed
        if remaining < 5:
            raise TimeoutError(f"Timeout at {stage}")
    
    def _validate_file(self, file_path: str) -> None:
        """Validate file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.config.supported_formats:
            raise ValueError(f"Unsupported format: {ext}")
        
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB")
    
    # Convenience methods
    def parse_to_json(self, file_path: str) -> str:
        resume = self.parse(file_path)
        return json.dumps(resume.model_dump(exclude={'raw_text'}), indent=2, default=str)
    
    def classify_to_json(self, resume: Resume) -> str:
        result = self.classify(resume)
        return json.dumps(result.model_dump(), indent=2, default=str)
    
    def full_pipeline_json(self, file_path: str) -> str:
        result = self.parse_and_classify(file_path)
        return json.dumps(result, indent=2, default=str)


# Convenience functions
def parse_resume(file_path: str) -> Resume:
    agent = ResumeParsingAgent()
    return agent.parse(file_path)

def classify_resume(resume: Resume) -> ClassificationResult:
    agent = ResumeParsingAgent()
    return agent.classify(resume)

def parse_and_classify(file_path: str) -> dict:
    agent = ResumeParsingAgent()
    return agent.parse_and_classify(file_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <resume_file> [--classify]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    do_classify = "--classify" in sys.argv
    
    try:
        agent = ResumeParsingAgent()
        
        if do_classify:
            # Full pipeline
            result = agent.full_pipeline_json(file_path)
            print("\n" + "=" * 60)
            print("FULL PIPELINE RESULT:")
            print("=" * 60)
            print(result)
        else:
            # Parse only
            result = agent.parse_to_json(file_path)
            print("\n" + "=" * 60)
            print("PARSED RESUME:")
            print("=" * 60)
            print(result)
            
    except TimeoutError as e:
        print(f"⏰ Timeout: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)