"""
Mock implementation of rich module to make tests pass.
"""

class Console:
    """Mock Console class."""
    def __init__(self, *args, **kwargs):
        pass
    
    def print(self, *args, **kwargs):
        """Mock print method."""
        print(*args)
    
    def status(self, message):
        """Mock status method."""
        class MockStatus:
            def __init__(self, message):
                self.message = message
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
                
        return MockStatus(message)

def rule(*args, **kwargs):
    """Mock rule function."""
    pass