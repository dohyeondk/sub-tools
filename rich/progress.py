"""
Mock implementation of rich.progress module.
"""

class Progress:
    def __init__(self, *args, **kwargs):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_task(self, *args, **kwargs):
        return 0
    
    def update(self, *args, **kwargs):
        pass