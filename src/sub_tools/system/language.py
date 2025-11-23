import pycountry


def get_language_name(language_code: str) -> str:
    """
    Returns the full English name of a language using its two-letter ISO 639-1 code.
    """
    return pycountry.languages.get(alpha_2=language_code).name
