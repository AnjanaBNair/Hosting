import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easygui
from webdriver_manager.chrome import ChromeDriverManager

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)  # Print to console for debugging
    return log_entry

# Set up the WebDriver using webdriver_manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# Open the log file
log_file_path = "test/selenium_login_test_results.txt"
with open(log_file_path, "w") as log_file:
    try:
        log_message("Starting the Selenium test...")

        driver.maximize_window()
        log_message("Browser window maximized.")

        # Navigate to the login page
        driver.get("http://127.0.0.1:8000/login/")
        log_message("Navigated to the login page.")

        # Wait for the email input field to be present
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        log_message("Email input field is visible.")

        # Input the email
        email_input.send_keys("chandralekha5064@gmail.com")
        log_message("Entered email: chandralekha5064@gmail.com")

        # Wait for the password input field to be present
        password_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        log_message("Password input field is visible.")

        # Input the password
        password_input.send_keys("Lekha@123")
        log_message("Entered password: ********")

        # Wait for the login button to be clickable
        login_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "submit"))
        )
        login_button.click()
        log_message("Clicked the login button.")

        # Wait for the page to load and check the URL
        WebDriverWait(driver, 40).until(EC.title_contains("Next-Edge"))
        log_message("Page loaded after login attempt.")

        # Check if login was successful
        if driver.current_url == "http://127.0.0.1:8000/baseindex/":
            easygui.msgbox("Login Successful Test Passed..!!!")
            log_message("Login successful!")
        else:
            easygui.msgbox("Test Failed...!!!")
            log_message("Login failed or unexpected redirect.")

    except Exception as e:
        log_message(f"An error occurred: {e}")
        easygui.msgbox(f"An error occurred: {e}")

    finally:
        # Close the browser
        time.sleep(3)  # Wait for 3 seconds to see the result
        driver.quit()
        log_message("Browser closed. Test completed.")

print("Test completed. Results have been written to", log_file_path)
