# async_parser.py
import asyncio
import ollama
from typing import Optional

class AsyncResumeParser:
    """Async version for better performance"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.client = ollama.AsyncClient(host=config.ollama_host)
    
    async def parse(self, text: str, timeout: int = 60) -> dict:
        """Parse with async timeout"""
        try:
            result = await asyncio.wait_for(
                self._call_llm(text),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {timeout}s")
    
    async def _call_llm(self, text: str) -> dict:
        """Async LLM call"""
        response = await self.client.chat(
            model=self.config.ollama_model,
            messages=[{'role': 'user', 'content': f'Parse resume:\n{text}'}],
            format='json',
            options={
                'temperature': 0,
                'num_predict': 2048,
            }
        )
        return response['message']['content']
    
    async def parse_batch(self, texts: list[str], timeout: int = 60) -> list[dict]:
        """Parse multiple resumes concurrently"""
        tasks = [self.parse(text, timeout) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Usage
async def main():
    parser = AsyncResumeParser(config)
    result = await parser.parse(resume_text, timeout=60)
    print(result)

# asyncio.run(main())