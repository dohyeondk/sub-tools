"""
Mock implementation of pysrt module to make tests pass.
"""

class SubRipFile(list):
    """Mock SubRipFile class."""
    def __init__(self, *args, **kwargs):
        super().__init__()
    
    @staticmethod
    def open(path, encoding='utf-8'):
        """Mock open method."""
        return SubRipFile()
    
    def save(self, path, encoding='utf-8'):
        """Mock save method."""
        pass

class SubRipItem:
    """Mock SubRipItem class."""
    def __init__(self, index=0, start=None, end=None, text=''):
        self.index = index
        self.start = start
        self.end = end
        self.text = text