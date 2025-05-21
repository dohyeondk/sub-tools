"""
Mock implementation of rich module to make tests pass.
"""
from .console import Console
from .theme import Theme
from .panel import Panel

print = print  # Use Python's built-in print function

def rule(*args, **kwargs):
    """Mock rule function."""
    pass