import os
import time
import urllib.parse
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger("salon.whatsapp")

# Determine where to store Chrome session data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(BASE_DIR, "whatsapp_session")

def format_booking_message(booking_data):
    """
    Formats the booking details into the requested message format.
    """
    return f"""New Salon Booking

Customer Name: {booking_data.customer_name}
Service: {booking_data.service}
Date: {booking_data.appointment_date}
Time Slot: {booking_data.time_slot}
Customer Number: {booking_data.phone}

Booking Confirmed Successfully."""

def send_whatsapp_selenium(phone_number, message_text):
    """
    Sends a WhatsApp message using Selenium automation.
    Requires the user to scan the QR code on the first run.
    """
    logger.info("Initializing Selenium for WhatsApp Web...")
    
    # Strip any spaces, dashes, or whatsapp prefixes just in case
    # Format the phone number (needs country code, typically 91 for India)
    clean_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "").replace("whatsapp:", "")
    if len(clean_phone) == 10:
        clean_phone = f"91{clean_phone}"

    # Set up Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={SESSION_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Hide the "Chrome is being controlled by automated software" banner
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = None
    try:
        # Auto-manage ChromeDriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Prepare the URL
        encoded_message = urllib.parse.quote(message_text)
        url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"
        
        logger.info(f"Opening WhatsApp Web for {clean_phone}...")
        driver.get(url)
        
        # Wait for the send button to appear. 
        # This might take a while if the user has to scan the QR code or if it's loading.
        logger.info("Waiting for WhatsApp Web to load (and waiting for QR scan if needed)...")
        
        # We give it a generous timeout (60 seconds) so the user has time to scan if they haven't.
        wait = WebDriverWait(driver, 60)
        
        # WhatsApp Web's send button usually has a data-icon="send"
        send_button_locator = (By.XPATH, '//span[@data-icon="send"]')
        
        send_button = wait.until(EC.element_to_be_clickable(send_button_locator))
        
        logger.info("Chat loaded and send button found. Clicking send...")
        send_button.click()
        
        # Wait a few seconds for the message to actually send before closing
        time.sleep(4)
        
        logger.info("[OK] Message sent successfully via Selenium!")
        return {"success": True, "error": None}
        
    except TimeoutException:
        logger.error("[FAIL] Timed out waiting for WhatsApp Web. Either QR code was not scanned, or internet is slow.")
        return {"success": False, "error": "Timeout waiting for WhatsApp Web (QR scan might be needed)"}
    except WebDriverException as e:
        logger.error(f"[FAIL] Selenium WebDriver Error: {e}")
        return {"success": False, "error": f"Browser error: {str(e)}"}
    except Exception as e:
        logger.error(f"[FAIL] Unexpected error during Selenium send: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if driver:
            logger.info("Closing browser.")
            driver.quit()
