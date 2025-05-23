from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BaseConfig:
    """
    Base configuration class with common parameters.
    All configuration classes should inherit from this class.
    """
    directory: str = "tmp"