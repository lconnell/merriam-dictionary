import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from .config import LOGIN_TIMEOUT_MS, LOGIN_URL, PAGE_LOAD_TIMEOUT_MS, SAVED_WORDS_URL

logger = logging.getLogger(__name__)


def login_and_get_cookies(email: str, password: str) -> list[dict]:
    """
    Launches a headless Chromium browser, logs in to Merriam-Webster, and returns
    session cookies for use with downstream HTTP requests.

    Playwright is scoped only to authentication. All subsequent API calls use a
    plain requests.Session loaded with these cookies — no browser needed for
    pagination or dictionary lookups.

    Args:
        email: Merriam-Webster account email.
        password: Merriam-Webster account password.

    Returns:
        A list of cookie dicts from the authenticated browser context.

    Raises:
        RuntimeError: If login times out or fails.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logger.info("Navigating to login page...")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

            page.fill("#ul-email", email)
            page.fill("#ul-password", password)
            page.click("#ul-login")

            # Wait for redirect away from /login — indicates successful auth.
            page.wait_for_url(
                lambda url: "/login" not in url,
                timeout=LOGIN_TIMEOUT_MS,
            )
            logger.info("Logged in successfully.")

            # Navigate to saved-words to ensure all session cookies are fully set.
            page.goto(SAVED_WORDS_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

            cookies = context.cookies()
            logger.info("Extracted %d cookies from browser session.", len(cookies))
            return cookies

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Login timed out — verify credentials and site availability."
            ) from exc

        finally:
            browser.close()
