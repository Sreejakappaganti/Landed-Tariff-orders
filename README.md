# Assam AERC Orders Automation

This Python script automates the process of navigating to Assam Electricity Regulatory Commission's Orders section.

## Prerequisites

1. **Python 3.7 or higher** installed on your system
2. **Google Chrome** browser installed

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. The script uses ChromeDriver. If you encounter issues, you can install it via webdriver-manager (already in requirements.txt) or download manually from:
   - https://chromedriver.chromium.org/

## Usage

Run the script:
```bash
python assam_automation.py
```

## What the script does:

1. Opens https://www.cercind.gov.in/serc.html
2. Clicks on "Assam Electricity Regulatory Commission" link
3. Handles any popup alerts by clicking "OK"
4. Navigates to "Documents" section
5. Opens "Orders" section
6. Takes a screenshot and keeps browser open for 30 seconds for inspection

## Customization

### Run in Headless Mode
Edit `assam_automation.py` and uncomment line:
```python
# options.add_argument('--headless')
```

### Adjust Wait Times
Modify the `time.sleep()` values in the script to speed up or slow down navigation.

### Keep Browser Open Longer
Change the final `time.sleep(30)` value to desired seconds.

## Troubleshooting

- **ChromeDriver not found**: Install using `pip install webdriver-manager`
- **Element not found**: The website structure may have changed. Check the console output for available links.
- **Timeout errors**: Increase wait times in the script or check your internet connection.

## Output

- Console logs showing each navigation step
- Screenshot saved as `assam_orders_page.png`
