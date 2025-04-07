import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easygui
from webdriver_manager.chrome import ChromeDriverManager

# Create directory for logs if it doesn't exist
os.makedirs("test", exist_ok=True)

# Define log file path
log_file_path = "test/selenium_edit_schedule_test_results.txt"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)  # Print to console for debugging
    
    # Write to log file immediately
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry + "\n")
    
    return log_entry

try:
    # Initialize log file
    with open(log_file_path, "w") as log_file:
        log_file.write(f"Selenium Edit Schedule Test - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    log_message("Starting the Selenium test for expert login and schedule editing...")
    
    # Initialize Chrome WebDriver with options to avoid TensorFlow errors
    log_message("Initializing Chrome WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    log_message("Chrome WebDriver initialized successfully.")
    
    # Navigate to the expert auth page
    log_message("Navigating to the expert auth page...")
    driver.get("http://127.0.0.1:8000/expert/auth/")
    log_message("Navigated to the expert auth page.")
    
    # Wait for the login form to be visible
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "loginForm"))
    )
    log_message("Login form is visible.")
    
    # Enter login credentials
    log_message("Entering login credentials...")
    email_field = driver.find_element(By.NAME, "email")
    email_field.send_keys("arunkumar1990@gmail.com")
    
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys("Arunkumar@123")
    log_message("Login credentials entered.")
    
    # Submit the login form
    log_message("Submitting login form...")
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
    login_button.click()
    log_message("Login form submitted.")
    
    # Wait for redirect to dashboard
    WebDriverWait(driver, 10).until(
        EC.url_contains("expert/dashboard")
    )
    log_message("Successfully logged in and redirected to dashboard.")
    
    # Make sure the page is fully loaded
    time.sleep(2)
    
    # Ensure we're on the ongoing tab
    try:
        ongoing_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ongoing-tab"))
        )
        ongoing_tab.click()
        log_message("Clicked on the Ongoing Programs tab.")
        time.sleep(1)  # Wait for tab content to load
    except:
        log_message("Ongoing tab may already be active or not found.")
    
    # Find all Edit Schedule buttons with improved selector
    log_message("Looking for Edit Schedule buttons...")
    try:
        # Try different selectors to find the edit schedule buttons
        edit_schedule_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Edit Schedule')]")
        
        if not edit_schedule_buttons:
            edit_schedule_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'edit-schedule')]")
        
        if not edit_schedule_buttons:
            edit_schedule_buttons = driver.find_elements(By.XPATH, "//button[contains(@onclick, 'editSchedule')]")
            
        log_message(f"Found {len(edit_schedule_buttons)} Edit Schedule buttons.")
        
        if len(edit_schedule_buttons) == 0:
            # Take screenshot for debugging
            screenshot_path = "test/dashboard_screenshot.png"
            driver.save_screenshot(screenshot_path)
            log_message(f"No Edit Schedule buttons found. Screenshot saved to {screenshot_path}")
            
            # Get page source for debugging
            with open("test/page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            log_message("Page source saved to test/page_source.html")
            
            raise Exception("No Edit Schedule buttons found on the page.")
        
        # Choose which button to click
        target_index = min(11, len(edit_schedule_buttons) - 1)  # 12th button or last one
        target_button = edit_schedule_buttons[target_index]
        
        # Scroll to the button to make it visible
        driver.execute_script("arguments[0].scrollIntoView(true);", target_button)
        time.sleep(1)
        
        log_message(f"Clicking the button at index {target_index} (button {target_index + 1}).")
        target_button.click()
        log_message("Clicked the Edit Schedule button.")
        
    except Exception as e:
        log_message(f"Error finding or clicking Edit Schedule button: {str(e)}")
        raise
    
    # Wait for the schedule edit modal to appear
    log_message("Waiting for schedule edit modal...")
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "scheduleEditModal"))
    )
    log_message("Schedule edit modal is visible.")
    
    # Find the session time input field and update it to 10:00
    log_message("Looking for session time input field...")
    session_time_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "edit_session_time"))
    )
    
    # Clear the existing value and set the new time
    session_time_input.clear()
    time.sleep(0.5)  # Small pause after clearing
    session_time_input.send_keys("10:00")
    log_message("Updated session time to 10:00.")
    
    # Find and click the Save Changes button
    log_message("Looking for Save Changes button...")
    save_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Save Changes')]"))
    )
    save_button.click()
    log_message("Clicked the Save Changes button.")
    
    # Wait for the success message or modal to close
    success = False
    
    # Try multiple ways to detect success
    try:
        # First try to wait for a success alert if using SweetAlert
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "swal2-success"))
        )
        log_message("Success alert appeared.")
        
        # Click the OK button if present
        ok_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "swal2-confirm"))
        )
        ok_button.click()
        log_message("Clicked OK on success alert.")
        success = True
    except Exception as e:
        log_message(f"No success alert found: {str(e)}")
        
        # If no alert, check if the modal closed
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.ID, "scheduleEditModal"))
            )
            log_message("Schedule edit modal closed after saving.")
            success = True
        except Exception as e2:
            log_message(f"Modal did not close: {str(e2)}")
            
            # As a last resort, check if there's any success message on the page
            try:
                success_messages = driver.find_elements(By.XPATH, "//*[contains(text(), 'success') or contains(text(), 'Success')]")
                if success_messages:
                    log_message(f"Found success message: {success_messages[0].text}")
                    success = True
            except:
                pass
    
    # Final success/failure message
    if success:
        log_message("Test Passed: Successfully edited the program schedule!")
        easygui.msgbox("Test Passed: Successfully edited the program schedule!")
    else:
        log_message("Test Failed: Could not confirm if schedule was updated successfully.")
        easygui.msgbox("Test Failed: Could not confirm if schedule was updated successfully.")

except Exception as e:
    error_message = f"An error occurred: {str(e)}"
    log_message(error_message)
    easygui.msgbox(error_message)

finally:
    # Close the browser
    try:
        time.sleep(3)  # Wait for 3 seconds to see the result
        driver.quit()
        log_message("Browser closed. Test completed.")
    except Exception as close_error:
        log_message(f"Error closing browser: {close_error}")

print("Test completed. Results have been written to", log_file_path) 