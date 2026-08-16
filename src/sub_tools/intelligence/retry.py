def backoff(attempt: int) -> int:
    """
    Wait long enough for a capacity problem to clear.

    "High demand" responses persist for far longer than the one to four seconds
    an unscaled backoff would wait.
    """
    return min(60, 5 * 2**attempt)
