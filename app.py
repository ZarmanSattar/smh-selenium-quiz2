from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
import time
import re

app = Flask(__name__)

REGISTRATION = "FA23-BAI-053"
NEWS_SOURCE = "Sydney Morning Herald"
NEWS_URL = "https://www.smh.com.au"


def get_chrome_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def search_smh(keyword):
    """Use Selenium to search SMH and return the first result URL."""
    driver = get_chrome_driver()
    first_url = None
    try:
        search_url = f"https://www.smh.com.au/search?query={keyword.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(3)

        # Try to find search result links
        wait = WebDriverWait(driver, 10)
        # SMH search results are typically in article cards
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/']")

        for link in links:
            href = link.get_attribute("href")
            if href and "smh.com.au" in href and href != NEWS_URL + "/":
                # Filter out nav, footer, and non-article links
                if any(seg in href for seg in [
                    "/national/", "/world/", "/politics/", "/business/",
                    "/technology/", "/sport/", "/entertainment/", "/lifestyle/",
                    "/environment/", "/culture/", "/federal-politics/"
                ]):
                    first_url = href
                    break

        # Fallback: grab any smh article link
        if not first_url:
            for link in links:
                href = link.get_attribute("href")
                if href and "smh.com.au" in href and len(href) > 30:
                    if href.startswith("https://www.smh.com.au/") and href != "https://www.smh.com.au/":
                        first_url = href
                        break

    finally:
        driver.quit()

    return first_url


def scrape_article(url):
    """Scrape article text from the given URL using requests + BeautifulSoup."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try article body selectors common on SMH
        article_body = (
            soup.find("div", {"data-testid": "article-body"})
            or soup.find("div", class_=re.compile(r"article|story|content|body", re.I))
            or soup.find("article")
        )

        if article_body:
            paragraphs = article_body.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        return text

    except Exception as e:
        return ""


def summarize(text, num_sentences=4):
    """Simple extractive summary: return first N sentences."""
    if not text:
        return "Could not extract article content."

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

    summary = " ".join(sentences[:num_sentences])
    return summary if summary else "Could not summarize article."


@app.route("/get", methods=["GET"])
def get_news():
    keyword = request.args.get("keyword", "").strip()

    if not keyword:
        return jsonify({"error": "keyword parameter is required"}), 400

    try:
        # Step 1: Search SMH for keyword
        article_url = search_smh(keyword)

        if not article_url:
            return jsonify({
                "registration": REGISTRATION,
                "newssource": NEWS_SOURCE,
                "keyword": keyword,
                "url": "",
                "summary": "No results found for the given keyword."
            })

        # Step 2: Scrape article
        article_text = scrape_article(article_url)

        # Step 3: Summarize
        summary = summarize(article_text)

        return jsonify({
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": article_url,
            "summary": summary
        })

    except Exception as e:
        return jsonify({
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE,
            "keyword": keyword,
            "url": "",
            "summary": f"Error: {str(e)}"
        }), 500


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "registration": REGISTRATION,
        "service": f"{NEWS_SOURCE} News Scraper API",
        "usage": "/get?keyword=your_keyword"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000, debug=False)
