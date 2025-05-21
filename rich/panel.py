"""
Mock implementation of rich.panel module.
"""

class Panel:
    def __init__(self, content, *args, **kwargs):
        self.content = content
        
    def __str__(self):
        return str(self.content) if hasattr(self, 'content') else ""