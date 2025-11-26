"""
Requirements:
pip install selenium
Download ChromeDriver matching your Chrome version and ensure it's on PATH.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import sys

def test_apply_save15():
    options = Options()
    options.add_argument("--headless=new")  # remove headless while debugging
    driver = webdriver.Chrome(options=options)
    try:
        # load local file (update path)
        driver.get("file:///C:/Users/unikh/Desktop/autonomous-qa-agent/assets/checkout.html")
        time.sleep(0.5)

        # Add product p1 and p2 to cart
        driver.find_element(By.ID, "add-p1").click()
        driver.find_element(By.ID, "add-p2").click()
        time.sleep(0.2)

        # read pre-discount total
        total_el = driver.find_element(By.ID, "total")
        pre_total = float(total_el.text)

        # apply discount SAVE15
        discount_input = driver.find_element(By.ID, "discount")
        discount_input.clear()
        discount_input.send_keys("SAVE15")
        driver.find_element(By.ID, "apply-discount").click()
        time.sleep(0.2)

        post_total = float(driver.find_element(By.ID, "total").text)

        # expected: 15% off
        expected = round(pre_total * 0.85, 2)
        assert abs(post_total - expected) < 0.02, f"Expected {expected}, got {post_total}"
        print("PASS: Discount applied correctly")

    finally:
        driver.quit()

if __name__=="__main__":
    test_apply_save15()
