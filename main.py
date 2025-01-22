from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/scrape", status_code=200)
def scrape(url: Optional[str] = None):
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1. Primeira tentativa com requests
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to GET {url} ({e})"
        )

    # 2. Fallback com cloudscraper para status 202, 403, 503
    if resp.status_code in [202, 403, 503]:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed with cloudscraper: {e}"
            )

    # 3. Se ainda não for 200, retorna erro
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Request returned {resp.status_code}"
        )

    # 4. Parse HTML
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # --- Exemplo mais genérico: pegar todos os parágrafos ---
    paragraphs = soup.find_all("p")

    posts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text:
            posts.append({"paragraph": text})

    # Se quiser debug, descomente:
    # print(f"HTML snippet: {html[:500]}")
    # print(f"Status code final: {resp.status_code}")

    # 5. Retorna JSON
    return JSONResponse(content=posts, status_code=200)
