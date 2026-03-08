import logging
import time

import requests

from .config import WORDLIST_API_URL, WORDLIST_DELAY_SECS, WORDS_PER_PAGE

logger = logging.getLogger(__name__)

# Headers that signal an XHR request to the MW API. Stripped of browser
# fingerprint headers (sec-ch-ua, etc.) that are meaningless from requests.
_HEADERS: dict[str, str] = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest",
    "referer": "https://www.merriam-webster.com/saved-words",
}


def _build_session(cookies: list[dict]) -> requests.Session:
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))
    return session


def fetch_saved_words(cookies: list[dict]) -> list[str]:
    """
    Fetches all words from the authenticated user's MW saved-words list.

    Uses a plain HTTP session loaded with browser cookies — no browser needed.
    Paginates automatically until all pages are consumed.

    Args:
        cookies: Session cookies from a prior login_and_get_cookies() call.

    Returns:
        Ordered list of saved word strings (newest first).

    Raises:
        requests.HTTPError: On non-2xx responses from the wordlist API.
    """
    session = _build_session(cookies)
    all_words: list[str] = []
    total_pages: int = 0
    page: int = 1

    while True:
        params: dict[str, object] = {
            "search": "",
            "sort": "newest",
            "filter": "dt",
            "page": page,
            "perPage": WORDS_PER_PAGE,
        }
        response = session.get(WORDLIST_API_URL, params=params, headers=_HEADERS)
        response.raise_for_status()

        data = response.json().get("data", {}).get("data", {})

        if page == 1:
            total_pages = int(data.get("totalPages", 0))
            logger.info("Total pages: %d", total_pages)

        items: list[dict] = data.get("items", [])
        if not items:
            break

        words = [item["word"] for item in items if item.get("word")]
        all_words.extend(words)
        logger.info("Captured %d words from page %d / %d.", len(words), page, total_pages)

        if page >= total_pages:
            break

        page += 1
        time.sleep(WORDLIST_DELAY_SECS)

    logger.info("Total saved words captured: %d", len(all_words))
    return all_words
