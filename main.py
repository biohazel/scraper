from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

# SELENIUM + WEBDRIVER-MANAGER
import time
import uuid
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

    # 1) requests approach
    results = scrape_adnews_requests(url)
    # 2) fallback to selenium if empty
    if not results:
        results = scrape_adnews_selenium(url)

    # If still empty, return []
    if not results:
        print("No AdNews results found.")
        return JSONResponse(content=[], status_code=200)

    return JSONResponse(content=results, status_code=200)


def scrape_adnews_requests(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"[Requests GET] error: {e}")
        return []

    if resp.status_code in [202, 403, 503]:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            print(f"[Cloudscraper] error: {e}")
            return []

    if resp.status_code != 200:
        print(f"[Requests] returned {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # HOME layout
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")
    for art in articles_home:
        link_tag  = art.select_one("a")
        title_tag = art.select_one("div.title")
        desc_tag  = art.select_one("div.desc p")
        img_tag   = art.select_one("a img")

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

    # SEARCH layout
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
    options = Options()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Approach A: Omit user-data-dir entirely

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(5)

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # HOME layout
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")
    for art in articles_home:
        link_tag  = art.select_one("a")
        title_tag = art.select_one("div.title")
        desc_tag  = art.select_one("div.desc p")
        img_tag   = art.select_one("a img")

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

    # SEARCH layout
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
    Adjust selectors as needed.
    """
    if not link.startswith("http"):
        return ""

    try:
        detail_resp = requests.get(link, headers=headers, timeout=10)
        if detail_resp.status_code != 200:
            return ""
        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

        content_container = detail_soup.select_one("article.post, div.elementor-widget-container")
        if not content_container:
            return ""

        paragraphs = content_container.find_all("p")
        return "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    except Exception:
        return ""
