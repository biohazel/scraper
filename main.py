from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/scrape", status_code=200)
def scrape(url: Optional[str] = None):
    """
    Exemplo de endpoint:
      GET /scrape?url=https://makeone.com.br/blog/
    Retorna um array JSON de posts.
    """
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to GET {url} ({e})")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Request returned {resp.status_code}")

    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # Exemplo: extrair posts do blog MakeOne
    posts = []
    for article in soup.select('article.elementor-post'):
        title_elem   = article.select_one('.elementor-post__title a')
        date_elem    = article.select_one('.elementor-post-date')
        excerpt_elem = article.select_one('.elementor-post__excerpt p')

        title   = title_elem.text.strip() if title_elem else ''
        link    = title_elem['href'] if title_elem else ''
        date    = date_elem.text.strip() if date_elem else ''
        excerpt = excerpt_elem.text.strip() if excerpt_elem else ''

        posts.append({
            "title": title,
            "link": link,
            "date": date,
            "excerpt": excerpt
        })

    # Return the posts with an explicit 200
    return JSONResponse(content=posts, status_code=200)

