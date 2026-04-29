# utils/progress.py
import sys
import threading
import time

class ProgressIndicator:
    """Show progress while waiting for LLM"""
    
    def __init__(self, message: str = "Processing"):
        self.message = message
        self.running = False
        self.thread = None
    
    def start(self):
        """Start progress indicator"""
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()
    
    def stop(self):
        """Stop progress indicator"""
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write('\r' + ' ' * 50 + '\r')
        sys.stdout.flush()
    
    def _animate(self):
        """Animation loop"""
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        idx = 0
        start = time.time()
        
        while self.running:
            elapsed = time.time() - start
            sys.stdout.write(f'\r{chars[idx]} {self.message}... ({elapsed:.1f}s)')
            sys.stdout.flush()
            idx = (idx + 1) % len(chars)
            time.sleep(0.1)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


# Usage in parser
def parse_with_progress(self, text: str) -> Resume:
    with ProgressIndicator("Parsing resume"):
        return self.parser.parse(text)