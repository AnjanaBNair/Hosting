import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import easygui
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import numpy as np

# Create directory for logs if it doesn't exist
os.makedirs("test", exist_ok=True)

# Define log file path
log_file_path = "test/selenium_program_creation_test_results.txt"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)  # Print to console for debugging
    
    # Write to log file immediately
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry + "\n")
    
    return log_entry

# Create a sample image for testing
def create_sample_image(path, size=(300, 300)):
    try:
        # Create a simple colored image
        img = Image.new('RGB', size, color=(73, 109, 137))
        img.save(path)
        return True
    except Exception as e:
        log_message(f"Error creating sample image: {e}")
        return False

try:
    # Initialize log file
    with open(log_file_path, "w") as log_file:
        log_file.write(f"Selenium Program Creation Test - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    log_message("Starting the Selenium test for expert login and program creation...")
    
    # Initialize Chrome WebDriver
    log_message("Initializing Chrome WebDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
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
    
    # Navigate to create program page
    log_message("Navigating to create program page...")
    driver.get("http://127.0.0.1:8000/create_Expert_program/")
    log_message("Navigated to create program page.")
    
    # Wait for the program creation form to load
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "programForm"))
    )
    log_message("Program creation form loaded.")
    
    # Fill in program details
    log_message("Filling program details...")
    
    # Program Title
    title_field = driver.find_element(By.ID, "title")
    program_title = f"Test Program {datetime.now().strftime('%Y%m%d%H%M%S')}"
    title_field.send_keys(program_title)
    # log_message(f"Entered program title: {program_title}")
    
    # Program Category
    category_select = driver.find_element(By.ID, "category")
    category_select.click()
    category_option = driver.find_element(By.XPATH, "//option[@value='technical']")
    category_option.click()
    # log_message("Selected category: Technical Skills")
    
    # Mentor Name
    speaker_name = driver.find_element(By.ID, "speaker_name")
    speaker_name.send_keys("Arun Kumar")
    # log_message("Entered mentor name: Arun Kumar")
    
    # Mentor Designation
    speaker_designation = driver.find_element(By.ID, "speaker_designation")
    speaker_designation.click()
    designation_option = driver.find_element(By.XPATH, "//option[@value='industry_expert']")
    designation_option.click()
    # log_message("Selected designation: Industry Expert")
    
    # Mentor Organization
    organization_field = driver.find_element(By.ID, "speaker_organization")
    organization_field.send_keys("Test Organization")
    # log_message("Entered organization: Test Organization")
    
    # Mentor Profile
    profile_field = driver.find_element(By.ID, "speaker_profile")
    profile_field.send_keys("This is a test mentor profile with extensive experience in the field of technology and education. The mentor has worked with multiple organizations and has a proven track record of success.")
    # log_message("Entered mentor profile")
    
    # Create and upload mentor image
    sample_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test", "sample_profile.jpg")
    if create_sample_image(sample_image_path):
        speaker_image = driver.find_element(By.ID, "speaker_image")
        speaker_image.send_keys(os.path.abspath(sample_image_path))
    
    # Schedule Details
    start_date = driver.find_element(By.ID, "start_date")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date.send_keys(tomorrow)
    # log_message(f"Set start date to {tomorrow}")
    
    end_date = driver.find_element(By.ID, "end_date")
    next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    end_date.send_keys(next_week)
    # log_message(f"Set end date to {next_week}")
    
    session_time = driver.find_element(By.ID, "session_time")
    session_time.send_keys("14:00")
    # log_message("Set session time to 14:00")
    
    duration = driver.find_element(By.ID, "duration")
    duration.send_keys("2")
    # log_message("Set duration to 2 hours")
    
    # Meeting Details
    meeting_platform = driver.find_element(By.ID, "meeting_platform")
    meeting_platform.click()
    platform_option = driver.find_element(By.XPATH, "//option[@value='zoom']")
    platform_option.click()
    # log_message("Selected meeting platform: Zoom")
    
    meeting_link = driver.find_element(By.ID, "meeting_link")
    meeting_link.send_keys("https://zoom.us/test-meeting")
    # log_message("Entered meeting link")
    
    # Program Content - with longer description (at least 100 characters)
    description = driver.find_element(By.ID, "description")
    long_description = """This comprehensive program is designed to provide participants with in-depth knowledge and practical skills in the field of technology. 
    
    Throughout this program, participants will engage in hands-on activities, case studies, and interactive discussions that will enhance their understanding of key concepts and their application in real-world scenarios. 
    
    The program covers fundamental principles as well as advanced topics, ensuring that participants gain a well-rounded understanding of the subject matter. By the end of this program, participants will have developed the skills and knowledge necessary to excel in their professional endeavors.
    
    This test program was created through automated testing to verify the functionality of the program creation system."""
    
    description.send_keys(long_description)
    # log_message(f"Entered program description with {len(long_description)} characters")
    
    learning_outcomes = driver.find_element(By.ID, "learning_outcomes")
    learning_outcomes.send_keys("1. Understand key concepts and principles in the field\n2. Apply theoretical knowledge to practical scenarios\n3. Develop problem-solving skills\n4. Enhance critical thinking abilities\n5. Build a professional network with peers and industry experts")
    # log_message("Entered learning outcomes")
    
    prerequisites = driver.find_element(By.ID, "prerequisites")
    prerequisites.send_keys("Basic understanding of the subject matter. Familiarity with fundamental concepts is recommended but not required.")
    # log_message("Entered prerequisites")
    
    max_participants = driver.find_element(By.ID, "max_participants")
    max_participants.clear()
    max_participants.send_keys("20")
    # log_message("Set max participants to 20")
    
    log_message("All program details filled successfully")
    
    # Submit the form
    log_message("Submitting program creation form...")
    submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
    time.sleep(1)  # Small pause to ensure the button is clickable
    submit_button.click()
    log_message("Program creation form submitted.")
    
    # Wait for success message or redirect
    success = False
    
    # Try to detect success alert
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "swal2-success"))
        )
        # log_message("Success alert appeared.")
        
        # Click the OK button if present
        ok_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "swal2-confirm"))
        )
        ok_button.click()
        # log_message("Clicked OK on success alert.")
        success = True
    except Exception as alert_error:
        log_message(f"No success alert found: {alert_error}")
    
    # If no alert, check for redirect to dashboard
    if not success:
        try:
            WebDriverWait(driver, 10).until(
                EC.url_contains("expert/dashboard")
            )
            log_message("Redirected to dashboard after program creation.")
            success = True
        except Exception as redirect_error:
            log_message(f"Not redirected to dashboard: {redirect_error}")
    
    # Final success/failure message
    if success:
        log_message("Test Passed: Successfully created a new program!")
        easygui.msgbox("Test Passed: Successfully created a new program!")
    else:
        # Check for error messages on the page
        try:
            error_messages = driver.find_elements(By.CLASS_NAME, "error-message")
            visible_errors = [e.text for e in error_messages if e.is_displayed() and e.text.strip()]
            
            if visible_errors:
                error_text = "Form validation errors:\n" + "\n".join(visible_errors)
                log_message(error_text)
                easygui.msgbox(f"Test Failed: {error_text}")
            else:
                log_message("Test Failed: Program creation failed but no visible error messages found.")
                easygui.msgbox("Test Failed: Program creation failed but no visible error messages found.")
        except:
            log_message("Test Failed: Program creation may have failed.")
            easygui.msgbox("Test Failed: Program creation may have failed.")

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