import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
BASE_URL = "https://www.merriam-webster.com"
LOGIN_URL = f"{BASE_URL}/login"
SAVED_WORDS_URL = f"{BASE_URL}/saved-words"
WORDLIST_API_URL = f"{BASE_URL}/lapi/v1/wordlist/search"
DICT_API_BASE_URL = "https://dictionaryapi.com/api/v3/references/sd3/json"

# ---------------------------------------------------------------------------
# Playwright timeouts (milliseconds)
# ---------------------------------------------------------------------------
PAGE_LOAD_TIMEOUT_MS: int = 15_000
LOGIN_TIMEOUT_MS: int = 15_000

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
WORDS_PER_PAGE: int = 16

# ---------------------------------------------------------------------------
# Courtesy delays between outbound requests (seconds)
# ---------------------------------------------------------------------------
WORDLIST_DELAY_SECS: float = 0.5
DICT_DELAY_SECS: float = 0.3
DICT_MAX_WORKERS: int = 10

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT_FILE: str = "dictionary_output.json"
DEFAULT_LOG_FILE: str = "dictionary_scrape.log"


@dataclass(frozen=True)
class AppConfig:
    email: str
    password: str
    api_key: str
    output_file: str = DEFAULT_OUTPUT_FILE
    log_file: str | None = DEFAULT_LOG_FILE


def load_config(
    output_file: str = DEFAULT_OUTPUT_FILE,
    log_file: str | None = DEFAULT_LOG_FILE,
) -> AppConfig:
    """
    Reads required credentials from environment variables and returns an AppConfig.

    Raises:
        EnvironmentError: If any required environment variable is missing.
    """
    env: dict[str, str | None] = {
        "MW_EMAIL": os.environ.get("MW_EMAIL"),
        "MW_PASSWORD": os.environ.get("MW_PASSWORD"),
        "DICT_API_KEY": os.environ.get("DICT_API_KEY"),
    }
    missing = [key for key, value in env.items() if not value]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return AppConfig(
        email=env["MW_EMAIL"],  # type: ignore[arg-type]
        password=env["MW_PASSWORD"],  # type: ignore[arg-type]
        api_key=env["DICT_API_KEY"],  # type: ignore[arg-type]
        output_file=output_file,
        log_file=log_file,
    )
