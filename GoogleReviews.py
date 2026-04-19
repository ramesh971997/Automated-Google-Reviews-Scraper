from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import csv

PLACE_URL = "https://www.google.com/maps/place/Yellow+Pages/@-37.9725665,145.0531353,9z/data=!3m1!4b1!4m6!3m5!1s0x6ad643fb30969545:0xe510c2f7ca124c4f!8m2!3d-37.9725665!4d145.0531353!16s%2Fg%2F11h63hmd2j?entry=ttu&g_ep=EgoyMDI2MDQxNS4wIKXMDSoASAFQAw%3D%3D"

SELENIUM_PROFILE_DIR = r"C:\Users\USER\Desktop\chrome_selenium_profile"
OUTPUT_CSV = "google_maps_reviews.csv"

TARGET_REVIEWS = 1200
MAX_SCROLLS = 800
SCROLL_PAUSE = 1.5


def build_driver():
    os.makedirs(SELENIUM_PROFILE_DIR, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={SELENIUM_PROFILE_DIR}")
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def open_reviews_tab(driver):
    wait = WebDriverWait(driver, 25)
    print("Waiting for Reviews button...")

    review_selectors = [
        (By.XPATH, "//button[contains(@aria-label,'reviews') or contains(@aria-label,'Reviews')]"),
        (By.XPATH, "//button[contains(.,'Reviews') or contains(.,'reviews')]"),
        (By.CSS_SELECTOR, "button[aria-label*='Reviews']"),
        (By.CSS_SELECTOR, "button[aria-label*='reviews']"),
    ]

    for by, selector in review_selectors:
        try:
            reviews_btn = wait.until(EC.presence_of_element_located((by, selector)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", reviews_btn)
            time.sleep(1)

            try:
                reviews_btn.click()
                print(f"Clicked Reviews (normal click): {selector}")
            except Exception:
                driver.execute_script("arguments[0].click();", reviews_btn)
                print(f"Clicked Reviews (JS click): {selector}")

            time.sleep(5)
            return True
        except Exception:
            continue

    print("Could not find Reviews button.")
    return False


def get_reviews_scrollable_panel(driver):
    wait = WebDriverWait(driver, 30)
    time.sleep(3)

    panel_selectors = [
        (By.CSS_SELECTOR, 'div[role="feed"]'),
        (By.XPATH, '//div[@role="feed"]'),
        (By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf'),
        (By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf'),
        (By.XPATH, '//div[contains(@class,"m6QErb") and contains(@class,"DxyBCb")]'),
    ]

    for by, selector in panel_selectors:
        try:
            panel = wait.until(EC.presence_of_element_located((by, selector)))
            print(f"Found reviews panel using: {selector}")
            return panel
        except Exception:
            continue

    return None


def expand_visible_more_buttons(driver):
    more_selectors = [
        "button.w8nwRe.kyuRq",
    ]

    for selector in more_selectors:
        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.05)
            except Exception:
                pass


def scroll_reviews_panel(driver, panel, target_reviews=1200, max_scrolls=800, pause=1.5):
    print("Scrolling reviews panel...")

    last_count = 0
    stagnant_rounds = 0

    for i in range(max_scrolls):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel)
        time.sleep(pause)

        if i % 5 == 0:
            expand_visible_more_buttons(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
        current_count = len(cards)

        print(f"Scroll {i + 1}/{max_scrolls} | Loaded review cards: {current_count}")

        if current_count >= target_reviews:
            print(f"Reached target review count: {current_count}")
            break

        if current_count == last_count:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0

        if stagnant_rounds >= 15:
            print("No more new reviews loading.")
            break

        last_count = current_count


def click_more_inside_container(driver, container):
    try:
        more_buttons = container.find_elements(By.CSS_SELECTOR, "button.w8nwRe.kyuRq")
        for btn in more_buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.1)
            except Exception:
                pass
    except Exception:
        pass


def scrape_reviews(driver):
    print("Scraping reviews...")

    reviews_data = []
    seen = set()

    review_cards = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
    print(f"Found review cards: {len(review_cards)}")

    for idx, card in enumerate(review_cards, start=1):
        try:
            try:
                name = card.find_element(By.CSS_SELECTOR, "div.d4r55.fontTitleMedium").text.strip()
            except Exception:
                name = ""

            review_user = ""
            try:
                review_user_container = card.find_element(By.CSS_SELECTOR, "div.MyEned")
                click_more_inside_container(driver, review_user_container)
                review_user = review_user_container.text.strip()
            except Exception:
                review_user = ""

            review = ""
            try:
                review_container = card.find_element(By.CSS_SELECTOR, "div.wiI7pd")
                click_more_inside_container(driver, review_container)
                review = review_container.text.strip()
            except Exception:
                review = ""

            try:
                date = card.find_element(By.CSS_SELECTOR, "span.rsqaWe").text.strip()
            except Exception:
                date = ""

            stars = ""
            try:
                stars_el = card.find_element(By.CSS_SELECTOR, "span.kvMYJc")
                stars = stars_el.get_attribute("aria-label") or ""
            except Exception:
                stars = ""

            key = (name, review_user, review, date, stars)
            if (name or review_user or review or date or stars) and key not in seen:
                seen.add(key)
                reviews_data.append({
                    "Name": name,
                    "ReviewUser": review_user,
                    "Review": review,
                    "Date": date,
                    "Stars": stars
                })

        except Exception as e:
            print(f"Skipped review {idx}: {e}")

    return reviews_data


def save_to_csv(data, filename):
    if not data:
        print("No review data to save.")
        return

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Name", "ReviewUser", "Review", "Date", "Stars"]
        )
        writer.writeheader()
        writer.writerows(data)

    print(f"Saved {len(data)} reviews to {filename}")


def main():
    driver = None

    try:
        driver = build_driver()

        print("Opening Google Maps place URL...")
        driver.get(PLACE_URL)
        time.sleep(10)

        opened = open_reviews_tab(driver)
        if not opened:
            print("Failed to open Reviews tab.")
            return

        print("Reviews tab opened successfully.")

        panel = get_reviews_scrollable_panel(driver)
        if not panel:
            print("Could not find reviews scroll panel.")
            return

        scroll_reviews_panel(
            driver,
            panel,
            target_reviews=TARGET_REVIEWS,
            max_scrolls=MAX_SCROLLS,
            pause=SCROLL_PAUSE
        )

        expand_visible_more_buttons(driver)
        time.sleep(2)

        reviews = scrape_reviews(driver)
        save_to_csv(reviews, OUTPUT_CSV)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if driver:
            time.sleep(5)
            driver.quit()


if __name__ == "__main__":
    main()