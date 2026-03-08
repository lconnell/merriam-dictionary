import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import DICT_API_BASE_URL, DICT_DELAY_SECS, DICT_MAX_WORKERS
from .models import DictionaryEntry

logger = logging.getLogger(__name__)

_thread_local = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session

# Matches all MW API inline formatting tags: {it}, {/it}, {b}, {sc}, etc.
_FORMATTING_TAGS = re.compile(r"\{/?[a-z_]+\}")


def _strip_formatting(text: str) -> str:
    """Remove MW API inline formatting tags from example text."""
    return _FORMATTING_TAGS.sub("", text)


def _parse_examples(entry: dict) -> list[str]:
    """
    Extract unique example sentences from the nested def/sseq/dt/vis structure
    of a Merriam-Webster API entry.

    The MW response nests examples several levels deep:
      entry["def"] -> sseq -> sense_group -> sense_entry -> dt -> vis -> t
    """
    examples: list[str] = []

    for def_block in entry.get("def", []):
        for sense_group in def_block.get("sseq", []):
            for sense_entry in sense_group:
                # Each sense_entry is [sense_type, sense_info_dict]
                if len(sense_entry) < 2 or not isinstance(sense_entry[1], dict):
                    continue
                for dt_item in sense_entry[1].get("dt", []):
                    if not dt_item or dt_item[0] != "vis":
                        continue
                    for ex in dt_item[1]:
                        text = _strip_formatting(ex.get("t", "")).strip()
                        if text and text not in examples:
                            examples.append(text)

    return examples


def fetch_dictionary_entry(
    word: str,
    api_key: str,
    session: requests.Session,
) -> DictionaryEntry | None:
    """
    Fetches definition and example sentences for a single word from the
    Merriam-Webster Dictionary API.

    The API key is passed as a query parameter (not interpolated into the URL)
    to avoid key exposure in logs or proxies.

    Args:
        word: The word to look up.
        api_key: MW Dictionary API key.
        session: Shared requests.Session for connection reuse.

    Returns:
        A DictionaryEntry, or None if the word is not found or the request fails.
    """
    try:
        resp = session.get(f"{DICT_API_BASE_URL}/{word}", params={"key": api_key})
        resp.raise_for_status()
        entries = resp.json()
    except requests.HTTPError as exc:
        logger.error("HTTP error fetching '%s': %s", word, exc)
        return None
    except ValueError:
        logger.error("Invalid JSON response for '%s'.", word)
        return None

    if not entries or not isinstance(entries, list):
        logger.warning("No data returned for '%s'.", word)
        return None

    first = entries[0]
    if not isinstance(first, dict) or "meta" not in first:
        # API returns a list of string suggestions when the word is not found.
        logger.warning("'%s' not found; API returned suggestions.", word)
        return None

    shortdef = first.get("shortdef", [])
    return DictionaryEntry(
        word=word,
        description=shortdef[0] if shortdef else "",
        examples=_parse_examples(first),
    )


def _fetch_worker(args: tuple[int, str, str]) -> tuple[int, DictionaryEntry | None]:
    index, word, api_key = args
    session = _get_session()
    entry = fetch_dictionary_entry(word, api_key, session)
    time.sleep(DICT_DELAY_SECS)
    return index, entry


def enrich_words(words: list[str], api_key: str) -> list[DictionaryEntry]:
    """
    Fetches dictionary data for each word concurrently using a thread pool,
    with per-thread courtesy delays between requests.

    Each thread maintains its own requests.Session for connection reuse.
    Original word order is preserved in the returned list.

    Args:
        words: List of words to enrich.
        api_key: MW Dictionary API key.

    Returns:
        List of DictionaryEntry objects for successfully resolved words,
        in the same order as the input.
    """
    results_map: dict[int, DictionaryEntry] = {}
    total = len(words)
    completed = 0

    with ThreadPoolExecutor(max_workers=DICT_MAX_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_worker, (i, word, api_key)): word
            for i, word in enumerate(words)
        }
        for future in as_completed(futures):
            completed += 1
            index, entry = future.result()
            if entry:
                results_map[index] = entry
            logger.info("Processed word %d / %d: %s", completed, total, futures[future])

    results = [results_map[i] for i in sorted(results_map)]
    logger.info("Enriched %d / %d words.", len(results), total)
    return results
