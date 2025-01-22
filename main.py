from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/scrape")
def scrape(url: Optional[str] = None):
    """
    Usage Example:
      GET /scrape?url=https://adnews.com.br/
      GET /scrape?url=https://adnews.com.br/?s=inteligencia+artificial

    Returns a JSON array of news objects (title, url, description, image).
    """

    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    # *** Only proceed if URL is from adnews.com.br ***
    if "adnews.com.br" not in url:
        raise HTTPException(
            status_code=400,
            detail="This scraper is only configured for adnews.com.br"
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    # 1) First attempt with requests
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to GET {url} ({e})"
        )

    # 2) If status = 202, 403, or 503, try fallback with cloudscraper
    if resp.status_code in [202, 403, 503]:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed with cloudscraper: {e}"
            )

    # 3) If not status 200, error out
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Request returned {resp.status_code}"
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # 4.1. Layout for AdNews Home:
    #     "div.lista-ultimas.row div.col-12.col-lg-6"
    # ------------------------------------------------------------------
    articles_home = soup.select("div.lista-ultimas.row div.col-12.col-lg-6")

    results = []
    for art in articles_home:
        link_tag = art.select_one("a")
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

    # ------------------------------------------------------------------
    # 4.2. If none found, try layout for search results:
    #     "section.elementor-section div.elementor-post"
    # ------------------------------------------------------------------
    if not results:
        articles_search = soup.select("section.elementor-section div.elementor-post")
        for post in articles_search:
            link_tag = post.select_one("a.elementor-post__thumbnail__link, a.elementor-post__read-more, a.elementor-post__title__link")
            title_tag = post.select_one(".elementor-post__title a")
            desc_tag  = post.select_one(".elementor-post__excerpt p")
            img_tag   = post.select_one(".elementor-post__thumbnail__link img")

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

    # ------------------------------------------------------------------
    # 5) If still empty, maybe new layout or no results.
    # ------------------------------------------------------------------
    if not results:
        print("No AdNews results found with known selectors.")
        return JSONResponse(content=[], status_code=200)

    return JSONResponse(content=results, status_code=200)
