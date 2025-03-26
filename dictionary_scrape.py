import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Retrieve credentials from environment variables
EMAIL = os.environ.get("MW_EMAIL")
PASSWORD = os.environ.get("MW_PASSWORD")
if not EMAIL or not PASSWORD:
    raise EnvironmentError("Please set MW_EMAIL and MW_PASSWORD environment variables.")

# Set up Selenium; remove headless option if you want to debug visually
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

try:
    # 1. Open the login page and perform login.
    driver.get("https://www.merriam-webster.com/login")
    WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "ul-email")))
    driver.find_element(By.ID, "ul-email").send_keys(EMAIL)
    driver.find_element(By.ID, "ul-password").send_keys(PASSWORD)
    login_button = driver.find_element(By.ID, "ul-login")
    driver.execute_script("arguments[0].click();", login_button)
    
    # 2. Wait until the URL changes (indicating successful login)
    WebDriverWait(driver, 3).until(lambda d: "/login" not in d.current_url)
    print("✅ Logged in successfully!")
    
    # 3. Navigate to the saved words page to ensure session cookies are set.
    driver.get("https://www.merriam-webster.com/saved-words")
    WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    # Extract cookies from the Selenium session.
    selenium_cookies = driver.get_cookies()
finally:
    driver.quit()

# 4. Set up a requests session with the extracted cookies.
session = requests.Session()
for cookie in selenium_cookies:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))

# 5. Set headers as observed from your fetch request.
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

# 6. Define the base API endpoint URL.
BASE_API_URL = "https://www.merriam-webster.com/lapi/v1/wordlist/search?search=&sort=newest&filter=dt&page={page}&perPage=16"

# 7. Fetch page 1 to determine total pages.
page = 1
api_url = BASE_API_URL.format(page=page)
response = session.get(api_url, headers=headers)
data = response.json()

# Navigate the JSON to extract total pages.
total_pages = int(data.get("data", {}).get("data", {}).get("totalPages", 0))
print(f"Total pages: {total_pages}")

all_words = []

# 8. Loop over each page and extract words.
for page in range(1, total_pages + 1):
    api_url = BASE_API_URL.format(page=page)
    response = session.get(api_url, headers=headers)
    data = response.json()
    
    items = data.get("data", {}).get("data", {}).get("items", [])
    if not items:
        break  # No items on this page, exit loop.
    
    # Extract the 'word' field from each item.
    words = [item.get("word", "") for item in items if item.get("word")]
    all_words.extend(words)
    print(f"Captured {len(words)} words from page {page}.")

# 9. Output the collected words as JSON with a total count.
output = {
    "total_words": len(all_words),
    "saved_words": all_words
}
print(json.dumps(output, indent=2))