import pycountry


def get_language_name(language_code):
    """
    Retrieve the full English name of a language using its two-letter ISO 639-1 code.

    :param language_code: A two-letter ISO 639-1 language code (e.g., 'en' for English).
    :return: The English name of the matching language, such as 'English' or 'French'.
    :rtype: str
    """
    return pycountry.languages.get(alpha_2=language_code).name
