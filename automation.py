import os
import time
import requests
import urllib3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Disable SSL warnings globally for this automation
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- CONFIGURATION ----------
# Current file is in f:\States\Assam\assam_automation.py
# We want downloads in f:\States\downloads
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_ROOT = os.path.join(BASE_DIR, "downloads")

def get_state_download_path(state_name):
    """Creates and returns a specific path for the state in the downloads folder"""
    path = os.path.join(DOWNLOADS_ROOT, state_name)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def setup_driver(view_browser=True):
    """Initialize Chrome driver with optional visibility"""
    options = Options()
    if not view_browser:
        options.add_argument("--headless=new") 
    
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    
    # Disable images for faster loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def download_file(url, folder, filename=None):
    """Download file using requests and return True if successful"""
    if not filename:
        filename = url.split("/")[-1]
    
    filepath = os.path.join(folder, filename)
    print(f"Downloading {filename} via requests...")
    
    try:
        response = requests.get(url, stream=True, verify=False, timeout=30)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"File saved to {filepath}")
            return True
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Download error: {e}")
        return False

def process_assam(view_browser=True):
    """Automates Assam AERC website and returns True on success, False otherwise"""
    state_name = "Assam"
    download_path = get_state_download_path(state_name)
    driver = setup_driver(view_browser=view_browser)
    wait = WebDriverWait(driver, 15)
    
    success = False
    try:
        # Step 1: Navigate to the correct Orders page
        print(f"[{state_name}] Navigating to Orders page...")
        driver.get("https://aerc.gov.in/pages/sub/orders")
        
        # Step 2: Dynamically find all year links and pick the latest
        print(f"[{state_name}] Detecting available years...")
        year_links = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, 'year=')]")))
        
        available_years = []
        for link in year_links:
            year_text = link.text.strip()
            if year_text.isdigit():
                available_years.append((int(year_text), link))
        
        if not available_years:
            print(f"[{state_name}] No year links found.")
            return False

        # Sort years descending
        available_years.sort(key=lambda x: x[0], reverse=True)
        latest_year, latest_link = available_years[0]
        
        print(f"[{state_name}] Selecting latest available year: {latest_year}")
        driver.execute_script("arguments[0].click();", latest_link)
        
        # Step 3: Parse table for target PDF (TARIFF ORDER + APDCL)
        print(f"[{state_name}] Searching for TARIFF ORDER and APDCL in {latest_year}...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        rows = driver.find_elements(By.XPATH, "//tr[td]")
        matches = []
        for row in rows:
            row_text = row.text.upper()
            if "TARIFF ORDER" in row_text and "APDCL" in row_text:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 3:
                    date_info = cols[0].text.strip()
                    date_str = date_info.split('&')[0].strip() if '&' in date_info else date_info
                    
                    try:
                        order_date = datetime.strptime(date_str, "%d.%m.%Y")
                    except:
                        order_date = datetime.min
                    
                    try:
                        pdf_element = cols[2].find_element(By.TAG_NAME, "a")
                        pdf_url = pdf_element.get_attribute("href")
                        matches.append({"date": order_date, "url": pdf_url, "date_str": date_info})
                    except:
                        continue

        if not matches:
            print(f"[{state_name}] No matching PDF found.")
            return False

        # Sort matches by date descending
        matches.sort(key=lambda x: x['date'], reverse=True)
        target = matches[0]
        print(f"[{state_name}] Found most recent order from {target['date_str']}: {target['url']}")
        
        # Download the file
        success = download_file(target['url'], download_path)
        
    except Exception as e:
        print(f"[{state_name}] An error occurred: {e}")
        return False
    finally:
        driver.quit()
        print(f"[{state_name}] Process complete.")
        return success

if __name__ == "__main__":
    start_time = time.time()
    
    # Configuration
    SHOW_BROWSER = False  # Set to False to run in headless mode
    
    states_to_process = ["Assam"]
    results = {}
    
    for state in states_to_process:
        if state == "Assam":
            status = process_assam(view_browser=SHOW_BROWSER)
            results[state] = status
        else:
            print(f"Logic for {state} not yet implemented.")
            results[state] = False
    
    print("\n" + "="*40)
    print(f"{'STATE':<15} | {'AUTOMATION STATUS':<20}")
    print("-" * 40)
    for state, status in results.items():
        status_text = "Sucessfully Downloded" if status else "Failed to Download"
        print(f"{state:<15} | {status_text:<20}")
    print("="*40)
    print(f"Total time taken: {time.time() - start_time:.2f} seconds")
