import yaml
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import time

# Function to set up and configure Selenium WebDriver
def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service("/opt/homebrew/bin/chromedriver")  # Update to your correct path
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# Function to expand nested sections and collect all visible links
def expand_and_collect_links(driver, base_url):
    structure = {}

    # Recursive function to expand each item
    def expand_section(section):
        try:
            toggle = section.find_element(By.XPATH, ".//a[contains(@class, 'devsite-nav-toggle') and @aria-expanded='false']")
            toggle.click()
            WebDriverWait(driver, 2).until(EC.attribute_to_be(toggle, "aria-expanded", "true"))
            time.sleep(0.5)  # Short pause to allow new items to load
        except Exception as e:
            pass  # Ignore if the item has no expandable toggle

        # Collect links after expanding
        links = section.find_elements(By.XPATH, ".//li[@class='devsite-nav-item']/a[@href]")
        for link in links:
            link_text = link.text.strip() or "Unnamed Link"
            link_url = urljoin(base_url, link.get_attribute("href"))
            structure[link_text] = {"url": link_url, "internal_links": []}

    # Find all top-level sections in the sidebar
    sidebar_sections = driver.find_elements(By.XPATH, "//ul[@class='devsite-nav-list' and @menu='_book']//li[contains(@class, 'devsite-nav-item')]")
    
    # Expand and collect links recursively
    for section in sidebar_sections:
        expand_section(section)

    return structure

# Function to spider additional internal links for each primary link
def spider_links(driver, base_url, structure):
    for link_text, data in structure.items():
        link_url = data["url"]
        print(f"Spidering {link_text} -> {link_url}")

        # Open each primary link and capture additional internal links
        driver.get(link_url)
        time.sleep(2)  # Allow time for page to load

        # Capture all <a> tags with href on the page
        page_links = driver.find_elements(By.XPATH, "//a[@href]")
        for page_link in page_links:
            page_url = urljoin(base_url, page_link.get_attribute("href"))
            # Ensure the link is internal and not a duplicate
            if urlparse(page_url).netloc == urlparse(base_url).netloc and page_url not in data["internal_links"]:
                data["internal_links"].append(page_url)

        # Print debug information
        print(f"Captured {len(data['internal_links'])} additional links from {link_text}")

# Main function to crawl, expand, and spider links
def main(base_url, output_file="site_structure.yaml", headless=True):
    print(f"Starting crawl at {base_url}...")

    driver = setup_driver(headless=headless)
    driver.get(base_url)

    start_time = time.time()

    try:
        # Step 1: Expand all sections and collect primary sidebar links
        structure = expand_and_collect_links(driver, base_url)

        # Step 2: Spider each link to capture additional links
        spider_links(driver, base_url, structure)

        # Step 3: Save the structure to a YAML file
        with open(output_file, 'w') as f:
            yaml.dump(structure, f, default_flow_style=False)  # Save in a readable, nested YAML format

        print(f"Full site structure saved to {output_file}")

    finally:
        driver.quit()

    end_time = time.time()
    print(f"Crawling and spidering completed in {end_time - start_time:.2f} seconds.")

# Entry point for the script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a site with Selenium, expand sections, and spider links.")
    parser.add_argument('url', help="Base URL of the site to crawl.")
    parser.add_argument('--output', default="site_structure.yaml", help="Output YAML file for the site structure.")
    parser.add_argument('--headless', action='store_true', help="Run in headless mode.")
    args = parser.parse_args()

    main(args.url, output_file=args.output, headless=args.headless)

