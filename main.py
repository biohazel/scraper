from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

# SELENIUM + WEBDRIVER-MANAGER
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI()


@app.get("/scrape")
def scrape(url: Optional[str] = None):
    """
    Usage:
      GET /scrape?url=https://adnews.com.br/
      GET /scrape?url=https://adnews.com.br/?s=inteligencia+artificial

    Returns a JSON array of news objects:
      {
        "title": "...",
        "url": "...",
        "description": "...",
        "image": "...",
        # optionally "content": ...
      }

    1) Attempt normal scraping with requests + cloudscraper.
    2) If no results found, fallback to Selenium headless Chrome (JS).
    """

    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    # Only handle adnews.com.br
    if "adnews.com.br" not in url:
        raise HTTPException(
            status_code=400,
            detail="This scraper is only configured for adnews.com.br"
        )

    # First attempt with requests
    results = scrape_adnews_requests(url)

    # If we got nothing, fallback to Selenium
    if not results:
        results = scrape_adnews_selenium(url)

    # If still empty, return an empty array
    if not results:
        print("No AdNews results found with known selectors (requests + selenium).")
        return JSONResponse(content=[], status_code=200)

    return JSONResponse(content=results, status_code=200)


def scrape_adnews_requests(url: str):
    """
    Basic attempt using requests + cloudscraper for the AdNews homepage layout
    or any pages that do not require JavaScript for content.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1) requests
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"[Requests GET] error: {e}")
        return []

    # 2) fallback with cloudscraper if status code is 202/403/503
    if resp.status_code in [202, 403, 503]:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            print(f"[Cloudscraper] error: {e}")
            return []

    # If still not 200, bail out
    if resp.status_code != 200:
        print(f"[Requests] returned {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # PART A: Check "Home layout"
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")
    results = []

    for art in articles_home:
        link_tag = art.select_one("a")
        title_tag = art.select_one("div.title")
        desc_tag = art.select_one("div.desc p")
        img_tag = art.select_one("a img")

        if not link_tag or not title_tag:
            continue

        link  = link_tag.get("href", "").strip()
        title = title_tag.get_text(strip=True)
        desc  = desc_tag.get_text(strip=True) if desc_tag else ""
        img   = img_tag.get("src") if img_tag else ""

        results.append({
            "title": title,
            "url": link,
            "description": desc,
            "image": img
        })

    # PART B: If none found, check "Search layout"
    if not results:
        articles_search = soup.select("article.elementor-post")
        for post in articles_search:
            title_tag = post.select_one(".elementor-post__title a")
            desc_tag  = post.select_one(".elementor-post__excerpt p")
            img_tag   = post.select_one(".elementor-post__thumbnail__link img")

            if not title_tag:
                continue

            link  = title_tag.get("href", "").strip()
            title = title_tag.get_text(strip=True)
            desc  = desc_tag.get_text(strip=True) if desc_tag else ""
            img   = img_tag.get("src") if img_tag else ""

            results.append({
                "title": title,
                "url": link,
                "description": desc,
                "image": img
            })

    return results


def scrape_adnews_selenium(url: str):
    """
    If no results from requests, we suspect the page
    is JS-based (like search). We'll load in headless Chrome
    using webdriver-manager to auto-install ChromeDriver.
    """
    # Create a headless Chrome driver
    options = Options()
    options.headless = True
    # Add more arguments if needed:
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(5)  # wait for JavaScript to load

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 1) Try "Home layout"
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")
    for art in articles_home:
        link_tag = art.select_one("a")
        title_tag = art.select_one("div.title")
        desc_tag = art.select_one("div.desc p")
        img_tag = art.select_one("a img")

        if not link_tag or not title_tag:
            continue

        link  = link_tag.get("href", "").strip()
        title = title_tag.get_text(strip=True)
        desc  = desc_tag.get_text(strip=True) if desc_tag else ""
        img   = img_tag.get("src") if img_tag else ""

        results.append({
            "title": title,
            "url": link,
            "description": desc,
            "image": img
        })

    # 2) If still nothing, try "Search layout"
    if not results:
        articles_search = soup.select("article.elementor-post")
        for post in articles_search:
            title_tag = post.select_one(".elementor-post__title a")
            desc_tag  = post.select_one(".elementor-post__excerpt p")
            img_tag   = post.select_one(".elementor-post__thumbnail__link img")

            if not title_tag:
                continue

            link  = title_tag.get("href", "").strip()
            title = title_tag.get_text(strip=True)
            desc  = desc_tag.get_text(strip=True) if desc_tag else ""
            img   = img_tag.get("src") if img_tag else ""

            results.append({
                "title": title,
                "url": link,
                "description": desc,
                "image": img
            })

    return results


def scrape_detail_page(link: str, headers: dict) -> str:
    """
    (Optional) If you want to fetch full article text from detail pages.
    Adjust selectors to match the final layout of each article.
    """
    if not link.startswith("http"):
        return ""

    try:
        detail_resp = requests.get(link, headers=headers, timeout=10)
        if detail_resp.status_code != 200:
            return ""
        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

        # Example container for detail text
        content_container = detail_soup.select_one("article.post, div.elementor-widget-container")
        if not content_container:
            return ""

        paragraphs = content_container.find_all("p")
        full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return full_text

    except Exception:
        return ""
