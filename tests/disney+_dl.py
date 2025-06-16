import subprocess
import base64
import re
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Your credentials (use environment variables for security!)
email = "marcel.tran@yahoo.de"
password = "LudohateinengroßenPenis69"
profile_name = "Ludo"
target_url = input("Enter the URL of the Disney+ video you want to download: ")

# Start WebDriver and Chrome with Options and Capabilities
chrome_options = Options()
chrome_options.add_argument(
    'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15')

# Enable performance logging
capabilities = DesiredCapabilities.CHROME
capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

# Start the WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(
    service=service, options=chrome_options, desired_capabilities=capabilities)


def save_performance_logs(driver: webdriver.Chrome, output_file: str = "network_log.json"):
    """
    Extracts captured network-related event performance logs from a Chrome WebDriver session and saves specific network events to a file.

    Parameters:
    - driver (webdriver.Chrome): The Chrome WebDriver session from which to extract performance logs.
    - output_file (str, optional): The path to the file where the network events will be saved. Defaults to "network_log.json".

    The output file will contain a JSON array where each element represents a network event as a JSON object.
    """
    logs = driver.get_log("performance")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[")
        first = True
        for log in logs:
            network_log = json.loads(log["message"])["message"]
            if "Network.response" in network_log["method"] or "Network.request" in network_log["method"] or "Network.webSocket" in network_log["method"]:
                if not first:
                    f.write(",")
                f.write(json.dumps(network_log))
                first = False
        f.write("]")


def extract_m3u8_urls_from_logs(file_path: str = "network_log.json") -> str:
    """
    Extracts the M3U8 URL from the network logs file.

    Parameters:
    - file_path (str): The path to the network logs file.

    Returns:
    - str: The M3U8 URL found in the network logs.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        logs = json.loads(f.read())

    for log in logs:
        try:
            url = log["params"]["request"]["url"]
            if "ctr-all" in url and ".m3u8" in url:
                return url
        except KeyError:
            continue


def extract_license_url_from_logs(file_path="network_log.json") -> tuple[str, str]:
    """ 
    Extracts the license URL and authorization token from the network logs file.

    Parameters:
    - file_path (str): The path to the network logs file.

    Returns:
    - Tuple[str, str]: The license URL and authorization token found in the network logs.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        logs = json.loads(f.read())

    for log in logs:
        try:
            url = log["params"]["request"]["url"]
            if "obtain-license" in url:
                authorization = log["params"]["request"]["headers"]["Authorization"]
                return url, authorization
        except KeyError:
            continue


def replace_invalid_chars(title: str) -> str:
    """
    Replaces invalid characters in a string with similar-looking Unicode characters.s

    Args:
    - title (str): The string to replace invalid characters in.   

    Returns:
    - str: The string with invalid characters replaced.
    """
    invalid_chars = {'<': '\u02c2', '>': '\u02c3',
                     ':': '\u02d0', '"': '\u02ba', '/': '\u2044',
                     '\\': '\u29f9', '|': '\u01c0', '?': '\u0294',
                     '*': '\u2217'}

    return ''.join(invalid_chars.get(c, c) for c in title)


# Navigate to the login page
driver.get("https://www.disneyplus.com/identity/login/enter-email")

# Wait for and then click the cookie consent "Reject All" button
WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
    (By.ID, "onetrust-reject-all-handler"))).click()

# Enter email and submit
WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((By.ID, "email"))).send_keys(email)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Wait for password input to become visible, enter password, and submit
WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
    (By.ID, "password"))).send_keys(password)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Wait for the profile selection page and select the specified profile
WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
    (By.CSS_SELECTOR, ".sc-cIwbeI.lfQBTc")))

profiles = driver.find_elements(
    By.CSS_SELECTOR, "div[role='button'][aria-label]")
for profile in profiles:
    if profile.get_attribute("aria-label") == profile_name:
        time.sleep(2)
        profile.click()
        break

# Wait for the page to fully load
time.sleep(2)

# Navigate to the target web page
driver.get(target_url)

# Allow some time for the page and its network requests to fully load
time.sleep(10)
title = driver.find_element(
    By.CSS_SELECTOR, "div.title-field.body-copy").text
title = replace_invalid_chars(title)

# Retrieve the logs
save_performance_logs(driver)
m3u8 = extract_m3u8_urls_from_logs()
license_url, authorization = extract_license_url_from_logs()
os.remove("network_log.json")

driver.quit()

# download m3u8 file to check for pssh
header = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
}
# download m3u8 file to check for pssh
response = requests.get(m3u8, headers=header)
# Find 'URI="data:text/plain;base64,' in the response content
pattern = re.compile(r'URI="data:text/plain;base64,([^"]+)')
pssh = pattern.findall(response.text)

if pssh:
    pssh = pssh[0]

# Send the license request to get encryption keys
api_url = "https://cdrm-project.com/api"
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Ktesttemp, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
    'authorization': f'"{authorization}"', }
r = requests.post(api_url, headers=headers, json={
    "license": license_url, "pssh": pssh}).text

keys = []
try:
    extracted_keys = json.loads(r)["keys"]
except KeyError:
    print("No keys found in the response.")
    print(r)
    exit()
# for key in extracted_keys:
#     key = "--key " + key["key"]

# run N_m3u8DL-RE command to download the video
command = f'N_m3u8DL-RE.exe "{m3u8}" --save-name "{title}" --key {extracted_keys[0]["key"]} -M mkv --mp4-real-time-decryption'

# Execute the command without redirecting stdin, stdout, or stderr
# This allows for direct user interaction with the command
subprocess.run(command, shell=True)
