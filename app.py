from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import requests
from bs4 import BeautifulSoup
import time
import re

app = Flask(__name__)

REGISTRATION = "FA23-BAI-053"
NEWS_SOURCE = "Sydney Morning Herald"


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
    driver = get_chrome_driver()
    first_url = None
    try:
        driver.get("https://www.smh.com.au")
        time.sleep(4)

        # Dismiss consent popup using JavaScript
        try:
            driver.execute_script("""
                // Remove consent overlay
                var overlays = document.querySelectorAll('.fc-consent-root, .fc-dialog-overlay, [class*="consent"], [class*="modal"], [class*="overlay"]');
                overlays.forEach(function(el) { el.remove(); });
                // Restore body scroll
                document.body.style.overflow = 'auto';
            """)
            time.sleep(1)
        except Exception:
            pass

        # Use JavaScript to set value and trigger search
        try:
            driver.execute_script("""
                var input = document.querySelector('input[name="query"]');
                input.value = arguments[0];
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            """, keyword)
            time.sleep(1)

            # Submit the form via JS
            driver.execute_script("""
                var form = document.querySelector('input[name="query"]').closest('form');
                if (form) { form.submit(); }
            """)
        except Exception:
            # Fallback: navigate directly to search URL
            driver.get(f"https://www.smh.com.au/search?query={keyword.replace(' ', '+')}")

        time.sleep(7)

        # SMH article URL pattern
        article_pattern = re.compile(r'smh\.com\.au/.+-\d{8}-[a-z0-9]+\.html')

        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                if article_pattern.search(href):
                    first_url = href
                    break
            except Exception:
                continue

        # Fallback: any smh .html link
        if not first_url:
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if (
                        "smh.com.au" in href
                        and ".html" in href
                        and len(href) > 60
                        and href.count("-") > 4
                    ):
                        first_url = href
                        break
                except Exception:
                    continue

        # Last resort: print all links for debugging
        if not first_url:
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if "smh.com.au" in href and len(href) > 40:
                        first_url = href
                        break
                except Exception:
                    continue

    finally:
        driver.quit()

    return first_url


def scrape_article(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        article_body = (
            soup.find("div", {"data-testid": "article-body"})
            or soup.find("div", class_=re.compile(r"article|story|content|body", re.I))
            or soup.find("article")
        )
        paragraphs = article_body.find_all("p") if article_body else soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        return text
    except Exception:
        return ""


def summarize(text, num_sentences=4):
    if not text:
        return "Could not extract article content."
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
        article_url = search_smh(keyword)
        if not article_url:
            return jsonify({
                "registration": REGISTRATION,
                "newssource": NEWS_SOURCE,
                "keyword": keyword,
                "url": "",
                "summary": "No results found for the given keyword."
            })
        article_text = scrape_article(article_url)
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
