import os
import time
import requests
import urllib3
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Disable SSL warnings globally for this automation
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- CONFIGURATION ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_ROOT = os.path.join(BASE_DIR, "downloads")

def get_state_download_path(state_name):
    """Creates and returns a specific path for the state in the downloads folder"""
    path = os.path.join(DOWNLOADS_ROOT, state_name)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def clean_garbage_files(folder):
    """Deletes all non-PDF files from the folder to keep it clean"""
    print(f"Cleaning up non-PDF files in {folder}...")
    for file_path in glob.glob(os.path.join(folder, "*")):
        if not file_path.lower().endswith(".pdf"):
            try:
                os.remove(file_path)
                print(f"Deleted garbage file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Could not delete {file_path}: {e}")

def setup_driver(view_browser=True, download_path=None):
    """Initialize Chrome driver with optional visibility and download handling"""
    options = Options()
    if not view_browser:
        options.add_argument("--headless=new") 
    
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    
    # Preferences for handling downloads and PDFs
    prefs = {
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True  # Force PDF download instead of browser view
    }
    if download_path:
        prefs["download.default_directory"] = download_path
        
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Enable download behavior in headless mode
    if not view_browser and download_path:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_path
        })
        
    return driver

def download_file(url, folder, filename=None):
    """Download file using requests and return True if successful"""
    if not filename:
        filename = url.split("/")[-1]
        if '?' in filename: filename = filename.split('?')[0]
    
    # Ensure filename ends with .pdf
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
        
    filepath = os.path.join(folder, filename)
    print(f"Downloading {filename} via requests...")
    
    try:
        response = requests.get(url, stream=True, verify=False, timeout=60)
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
    state_name = "Assam"
    download_path = get_state_download_path(state_name)
    driver = setup_driver(view_browser=view_browser, download_path=download_path)
    wait = WebDriverWait(driver, 15)
    
    success = False
    try:
        print(f"[{state_name}] Navigating to Orders page...")
        driver.get("https://aerc.gov.in/pages/sub/orders")
        
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

        available_years.sort(key=lambda x: x[0], reverse=True)
        latest_year, latest_link = available_years[0]
        
        print(f"[{state_name}] Selecting latest available year: {latest_year}")
        driver.execute_script("arguments[0].click();", latest_link)
        
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
                        pdf_url = cols[2].find_element(By.TAG_NAME, "a").get_attribute("href")
                        matches.append({"date": order_date, "url": pdf_url, "date_str": date_info})
                    except:
                        continue

        if not matches:
            print(f"[{state_name}] No matching PDF found.")
            return False

        matches.sort(key=lambda x: x['date'], reverse=True)
        target = matches[0]
        print(f"[{state_name}] Found latest order: {target['url']}")
        success = download_file(target['url'], download_path)
        
    except Exception as e:
        print(f"[{state_name}] Error: {e}")
        success = False
    finally:
        driver.quit()
        clean_garbage_files(download_path)
        return success

def process_up(view_browser=True):
    state_name = "UP"
    download_path = get_state_download_path(state_name)
    driver = setup_driver(view_browser=view_browser, download_path=download_path)
    wait = WebDriverWait(driver, 20)
    
    success = False
    try:
        print(f"[{state_name}] Navigating to UPERC Tariff Orders...")
        driver.get("https://www.uperc.org/Tariff_Order_Users.aspx")
        time.sleep(2)
        
        links = driver.find_elements(By.XPATH, "//a[@class='aaa']")
        matches = []
        for link in links:
            text = link.text.upper()
            url = link.get_attribute("href")
            # Requirement: "State Discoms Tariff order", latest, ignore "scanned", MUST be PDF
            if "STATE DISCOMS" in text and "TARIFF ORDER" in text and "SCANNED" not in text:
                if url and ".pdf" in url.lower():
                    matches.append({"text": link.text, "url": url})
        
        if not matches:
            print(f"[{state_name}] Trying previous years...")
            try:
                prev_years_link = driver.find_element(By.LINK_TEXT, "Previous Years")
                driver.execute_script("arguments[0].click();", prev_years_link)
                time.sleep(2)
                links = driver.find_elements(By.XPATH, "//a[@class='aaa']")
                for link in links:
                    text = link.text.upper()
                    url = link.get_attribute("href")
                    if "STATE DISCOMS" in text and "TARIFF ORDER" in text and "SCANNED" not in text:
                        if url and ".pdf" in url.lower():
                            matches.append({"text": link.text, "url": url})
            except: pass

        if not matches:
            print(f"[{state_name}] No matching order found.")
            return False

        target = matches[0]
        print(f"[{state_name}] Found latest order: {target['text']}")
        success = download_file(target['url'], download_path)
        
    except Exception as e:
        print(f"[{state_name}] Error: {e}")
        success = False
    finally:
        driver.quit()
        clean_garbage_files(download_path)
        return success

def process_meghalaya(view_browser=True):
    state_name = "Meghalaya"
    download_path = get_state_download_path(state_name)
    driver = setup_driver(view_browser=view_browser, download_path=download_path)
    
    success = False
    try:
        print(f"[{state_name}] Navigating to MSERC Tariff Orders...")
        driver.get("https://www.mserc.gov.in/tarifforders.html")
        time.sleep(2)
        
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        matches = []
        for link in links:
            text = link.text.upper()
            if "AGGREGATE REVENUE" in text and "CORRIGENDUM" not in text:
                matches.append({"text": link.text, "url": link.get_attribute("href")})
        
        if not matches:
            print(f"[{state_name}] No matching PDF found.")
            return False

        target = matches[0]
        print(f"[{state_name}] Found latest order: {target['text']}")
        success = download_file(target['url'], download_path)
        
    except Exception as e:
        print(f"[{state_name}] Error: {e}")
        success = False
    finally:
        driver.quit()
        clean_garbage_files(download_path)
        return success

def process_rajasthan(view_browser=True):
    state_name = "Rajasthan"
    download_path = get_state_download_path(state_name)
    driver = setup_driver(view_browser=view_browser, download_path=download_path)
    wait = WebDriverWait(driver, 20)
    
    success = False
    try:
        print(f"[{state_name}] Navigating to RERC website...")
        driver.get("https://rerc.rajasthan.gov.in/")
        
        try:
            orders_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@id, 'navbarDropdownMenuLink')][contains(text(), 'Orders')]")))
            orders_menu.click()
            tariff_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'dropdown-item')][contains(@href, 'tariff-orders')]")))
            tariff_link.click()
        except:
            driver.get("https://rerc.rajasthan.gov.in/rerc-user-files/tariff-orders")
        
        print(f"[{state_name}] Filtering for 'Aggregate Revenue'...")
        time.sleep(3)
        try:
            search_by = wait.until(EC.presence_of_element_located((By.ID, "BodyContent_ddl_searchBy")))
            Select(search_by).select_by_visible_text("Subject")
            keyword_input = driver.find_element(By.ID, "BodyContent_txt_keyword")
            keyword_input.clear()
            keyword_input.send_keys("Aggregate Revenue")
            driver.find_element(By.ID, "BodyContent_btn_submit").click()
            time.sleep(5) # Wait for results to load
        except: pass
        
        rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'table')]//tr[td]")
        if not rows: rows = driver.find_elements(By.XPATH, "//*[@id='BodyContent_rptorders']//tr")
        
        target_row = None
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 4:
                # Subject is usually in index 3
                subject_text = cells[3].text.upper()
                if "AGGREGATE REVENUE" in subject_text and "DISCOMS" in subject_text and "PETITION" not in subject_text:
                    target_row = row
                    print(f"[{state_name}] Found target row: {subject_text}")
                    break
        
        if target_row:
            # Prefer 'View' button as it usually opens a direct PDF URL
            try:
                view_btn = target_row.find_element(By.XPATH, ".//a[contains(@title, 'View')]")
                main_window = driver.current_window_handle
                view_btn.click()
                time.sleep(7)
                
                pdf_url = None
                for handle in driver.window_handles:
                    if handle != main_window:
                        driver.switch_to.window(handle)
                        url = driver.current_url
                        if url.lower().endswith('.pdf') or "rerc-user-files" in url.lower():
                            pdf_url = url
                        driver.close()
                        driver.switch_to.window(main_window)
                        break
                
                if pdf_url:
                    print(f"[{state_name}] Captured PDF URL: {pdf_url}")
                    success = download_file(pdf_url, download_path, filename="Rajasthan_Tariff_Order.pdf")
                else:
                    raise Exception("No PDF URL captured from View button")
            except Exception as e:
                print(f"[{state_name}] View button failed ({e}), trying Download button...")
                before_files = set(os.listdir(download_path))
                download_btn = target_row.find_element(By.XPATH, ".//a[contains(@title, 'Download') or contains(@id, 'LinkButton')]")
                driver.execute_script("arguments[0].click();", download_btn)
                
                # Wait up to 60 seconds for the download to finish
                print(f"[{state_name}] Waiting for browser download...")
                for i in range(60):
                    time.sleep(1)
                    after_files = set(os.listdir(download_path))
                    new_files = [f for f in (after_files - before_files) if not f.endswith(('.crdownload', '.tmp', '.htm'))]
                    if new_files:
                        print(f"[{state_name}] Downloaded via browser: {new_files[0]}")
                        success = True
                        break
        else:
            print(f"[{state_name}] No matching PDF found.")

    except Exception as e:
        print(f"[{state_name}] Error: {e}")
    finally:
        driver.quit()
        clean_garbage_files(download_path)
        return success

if __name__ == "__main__":
    start_time = time.time()
    SHOW_BROWSER = False  # Headless mode
    
    states_to_process = ["Assam", "UP", "Meghalaya", "Rajasthan"]
    results = {}
    
    for state in states_to_process:
        if state == "Assam": results[state] = process_assam(view_browser=SHOW_BROWSER)
        elif state == "UP": results[state] = process_up(view_browser=SHOW_BROWSER)
        elif state == "Meghalaya": results[state] = process_meghalaya(view_browser=SHOW_BROWSER)
        elif state == "Rajasthan": results[state] = process_rajasthan(view_browser=SHOW_BROWSER)
    
    print("\n" + "="*40)
    print(f"{'STATE':<15} | {'AUTOMATION STATUS':<20}")
    print("-" * 40)
    for state, status in results.items():
        print(f"{state:<15} | {'Successfully Downloaded' if status else 'Failed to Download'}")
    print("="*40)
    print(f"Total time taken: {time.time() - start_time:.2f} seconds")
