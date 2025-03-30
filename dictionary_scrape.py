import os
import json
import time
import requests
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------
# Argument Parsing & Logging Setup
# --------------------------
parser = argparse.ArgumentParser(description="Dictionary Scrape with logging and file output options")
parser.add_argument("--no-stdout", action="store_true", help="Disable logging to stdout")
parser.add_argument("--no-logfile", action="store_true", help="Disable logging to a file")
args = parser.parse_args()

# By default, both are enabled; disable if flags provided.
stdout_logging = not args.no_stdout
logfile_logging = not args.no_logfile

logger = logging.getLogger("dictionary_scrape")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

if stdout_logging:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

if logfile_logging:
    file_handler = logging.FileHandler("dictionary_scrape.log", mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.info("Starting dictionary scrape script.")

# --------------------------
# Environment Variables
# --------------------------
MW_EMAIL = os.environ.get("MW_EMAIL")
MW_PASSWORD = os.environ.get("MW_PASSWORD")
DICT_API_KEY = os.environ.get("DICT_API_KEY")
if not MW_EMAIL or not MW_PASSWORD or not DICT_API_KEY:
    logger.error("Please set MW_EMAIL, MW_PASSWORD, and DICT_API_KEY environment variables.")
    exit(1)

# --------------------------
# Part 1: Login via Selenium and Extract Cookies
# --------------------------
def login_and_get_cookies():
    """
    Uses Selenium to log in to Merriam-Webster and extracts session cookies.
    
    Returns:
        list: A list of cookies from the Selenium session.
    """
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    try:
        logger.info("Navigating to login page...")
        driver.get("https://www.merriam-webster.com/login")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "ul-email"))
        )
        driver.find_element(By.ID, "ul-email").send_keys(MW_EMAIL)
        driver.find_element(By.ID, "ul-password").send_keys(MW_PASSWORD)
        login_button = driver.find_element(By.ID, "ul-login")
        driver.execute_script("arguments[0].click();", login_button)
        
        # Wait until the URL changes from /login, indicating a successful login.
        WebDriverWait(driver, 5).until(lambda d: "/login" not in d.current_url)
        logger.info("✅ Logged in successfully!")
        
        # Navigate to the saved words page to ensure cookies are set.
        driver.get("https://www.merriam-webster.com/saved-words")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Extract cookies.
        cookies = driver.get_cookies()
        logger.info("Extracted cookies from Selenium session.")
        return cookies
    finally:
        driver.quit()

selenium_cookies = login_and_get_cookies()

# --------------------------
# Part 2: Fetch All Saved Words Using the Paginated API
# --------------------------
def fetch_saved_words(cookies):
    """
    Uses the extracted cookies and a paginated API to fetch all saved words.
    
    Args:
        cookies (list): Cookies extracted from the Selenium session.
    
    Returns:
        list: A list of saved words.
    """
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))
    
    BASE_API_URL = "https://www.merriam-webster.com/lapi/v1/wordlist/search?search=&sort=newest&filter=dt&page={page}&perPage=16"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Google Chrome\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.merriam-webster.com/saved-words"
    }
    
    # Fetch page 1 to determine total pages.
    all_words = []
    page = 1
    response = session.get(BASE_API_URL.format(page=page), headers=headers)
    data_page1 = response.json()
    total_pages = int(data_page1.get("data", {}).get("data", {}).get("totalPages", 0))
    logger.info(f"Total pages: {total_pages}")
    
    for page in range(1, total_pages + 1):
        api_url = BASE_API_URL.format(page=page)
        response = session.get(api_url, headers=headers)
        page_data = response.json()
        items = page_data.get("data", {}).get("data", {}).get("items", [])
        if not items:
            break
        for item in items:
            word = item.get("word", "")
            if word:
                all_words.append(word)
        logger.info(f"Captured {len(items)} words from page {page}.")
        time.sleep(0.5)  # be polite to the server
    
    logger.info(f"Total saved words captured: {len(all_words)}")
    return all_words

all_words = fetch_saved_words(selenium_cookies)

# --------------------------
# Part 3: Fetch Definition and Examples from the Dictionary API
# --------------------------
def fetch_dictionary_data(word):
    """
    For a given word, fetches its dictionary data including a short definition and example sentences.
    
    Args:
        word (str): The word to fetch data for.
    
    Returns:
        dict or None: A dictionary with keys 'word', 'description', and 'examples', or None if no data is found.
    """
    url = f"https://dictionaryapi.com/api/v3/references/sd3/json/{word}?key={DICT_API_KEY}"
    resp = requests.get(url)
    try:
        entries = resp.json()
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON for word '{word}'.")
        return None

    if not entries or not isinstance(entries, list):
        logger.warning(f"No data returned for '{word}'.")
        return None

    first_entry = entries[0]
    if not isinstance(first_entry, dict) or "meta" not in first_entry:
        logger.warning(f"Word '{word}' not found in dictionary API.")
        return None

    # Use the first short definition.
    shortdef_list = first_entry.get("shortdef", [])
    description = shortdef_list[0] if shortdef_list else ""
    
    # Extract example sentences from the 'def' section.
    examples = []
    for d in first_entry.get("def", []):
        sseq = d.get("sseq", [])
        for sense_group in sseq:
            for sense_entry in sense_group:
                if len(sense_entry) < 2:
                    continue
                sense_info = sense_entry[1]
                # Check that sense_info is a dict.
                if not isinstance(sense_info, dict):
                    continue
                dt_items = sense_info.get("dt", [])
                for dt_item in dt_items:
                    if dt_item and dt_item[0] == "vis":
                        # dt_item[1] is a list of examples.
                        for ex in dt_item[1]:
                            example_text = ex.get("t", "")
                            # Remove formatting tags.
                            example_text = example_text.replace("{it}", "").replace("{/it}", "")
                            if example_text and example_text not in examples:
                                examples.append(example_text)
    return {
        "word": word,
        "description": description,
        "examples": examples
    }

formatted_words = []
for word in all_words:
    logger.info(f"Processing dictionary data for: {word}")
    entry = fetch_dictionary_data(word)
    if entry:
        formatted_words.append(entry)
    time.sleep(0.3)  # to avoid rate limits

# --------------------------
# Part 4: Output Final Structured JSON and Save to File
# --------------------------
final_output = {
    "total_words": len(formatted_words),
    "data": formatted_words
}
final_json = json.dumps(final_output, indent=2)

# logger.info("Final Output:")
# logger.info(final_json)

# Print to stdout if enabled.
if stdout_logging:
    print(final_json)

# Save final output to a JSON file.
output_filename = "dictionary_output.json"
with open(output_filename, "w") as outfile:
    outfile.write(final_json)
logger.info(f"Final output saved to {output_filename}")