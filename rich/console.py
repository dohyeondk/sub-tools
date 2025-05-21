"""
Mock implementation of rich.console module.
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
    
    def log(self, *args, **kwargs):
        """Mock log method."""
        print(*args)