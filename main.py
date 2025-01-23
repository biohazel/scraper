from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

app = FastAPI()

@app.get("/scrape")
def scrape(url: Optional[str] = None):
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    if "adnews.com.br" not in url:
        raise HTTPException(
            status_code=400,
            detail="This scraper is only configured for adnews.com.br"
        )

    results = scrape_adnews_requests(url)

    if not results:
        results = scrape_adnews_selenium(url)

    if not results:
        return JSONResponse(content=[], status_code=200)

    return JSONResponse(content=results, status_code=200)

def scrape_adnews_requests(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code in [202, 403, 503]:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        return parse_articles(soup)

    except Exception as e:
        print(f"Request error: {str(e)}")
        return []

def scrape_adnews_selenium(url: str):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--single-process")
    options.add_argument("--headless=new")
    options.binary_location = "/usr/bin/chromium"

    service = Service(executable_path="/usr/lib/chromium/chromedriver")
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return parse_articles(soup)
        
    except Exception as e:
        print(f"Selenium error: {str(e)}")
        return []
        
    finally:
        if driver:
            driver.quit()

def parse_articles(soup):
    results = []
    
    # Home layout
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")
    for art in articles_home:
        link_tag = art.select_one("a")
        title_tag = art.select_one("div.title")
        desc_tag = art.select_one("div.desc p")
        img_tag = art.select_one("a img")

        if link_tag and title_tag:
            results.append({
                "title": title_tag.get_text(strip=True),
                "url": link_tag.get("href", "").strip(),
                "description": desc_tag.get_text(strip=True) if desc_tag else "",
                "image": img_tag.get("src") if img_tag else ""
            })

    # Search layout
    if not results:
        articles_search = soup.select("article.elementor-post")
        for post in articles_search:
            title_tag = post.select_one(".elementor-post__title a")
            desc_tag = post.select_one(".elementor-post__excerpt p")
            img_tag = post.select_one(".elementor-post__thumbnail__link img")

            if title_tag:
                results.append({
                    "title": title_tag.get_text(strip=True),
                    "url": title_tag.get("href", "").strip(),
                    "description": desc_tag.get_text(strip=True) if desc_tag else "",
                    "image": img_tag.get("src") if img_tag else ""
                })

    return results