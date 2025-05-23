class AppError(Exception):
    """
    Base exception class for the application.
    All custom exceptions should inherit from this class.
    """
    pass


class ValidationError(AppError):
    """
    Base exception for validation errors.
    """
    pass