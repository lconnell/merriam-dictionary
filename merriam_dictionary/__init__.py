"""
merriam_dictionary — export Merriam-Webster saved words with definitions.

Modules:
    auth        Playwright-based login and cookie extraction.
    wordlist    Paginated HTTP fetch of the user's saved-words list.
    dictionary  MW Dictionary API lookup and response parsing.
    models      DictionaryEntry dataclass.
    config      Constants, AppConfig dataclass, and env-var loader.
"""
