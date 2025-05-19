from pysrt import SubRipFile
from ..config.errors import ValidationError


def validate_threshold(value: int, threshold: int, message: str) -> None:
    """
    Validate that a value does not exceed a threshold.
    
    Args:
        value: The value to check
        threshold: The maximum allowed value
        message: Error message format with placeholders for {value} and {threshold}
    
    Raises:
        ValidationError: If validation fails
    """
    if value > threshold:
        raise ValidationError(message.format(value=value, threshold=threshold))


def validate_min_count(items: list, min_count: int, message: str) -> None:
    """
    Validate minimum number of items.
    
    Args:
        items: The list or sequence to check
        min_count: The minimum required count
        message: Error message format with placeholders for {found} and {min_count}
    
    Raises:
        ValidationError: If validation fails
    """
    if len(items) < min_count:
        raise ValidationError(message.format(found=len(items), min_count=min_count))