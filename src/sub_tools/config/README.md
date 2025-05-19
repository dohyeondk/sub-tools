# Configuration Module

This module provides base classes and utilities for configuration and validation across the application.

## Components

### BaseConfig

The `BaseConfig` class in `base.py` serves as the parent class for all configuration classes in the application. It provides common configuration parameters like:

- `directory`: Default directory for file operations

### Error Handling

The `errors.py` module provides a standardized approach to error handling:

- `AppError`: Base exception class for all application errors
- `ValidationError`: Base exception for validation errors

### Validation Utilities

The `validation.py` module contains common validation functions:

- `validate_threshold()`: Checks if a value exceeds a threshold
- `validate_min_count()`: Validates minimum counts in collections
- `parse_subtitles()`: Safely parses subtitle files
- `format_error_message()`: Standardizes error message formatting

## Usage

To create a new configuration class:

```python
from dataclasses import dataclass
from sub_tools.config.base import BaseConfig

@dataclass
class MyConfig(BaseConfig):
    """Configuration for my module."""
    my_param: int = 100
    another_param: str = "default"
```

To create custom errors:

```python
from sub_tools.config.errors import ValidationError

class MyValidationError(ValidationError):
    """Custom validation error for my module."""
    pass
```