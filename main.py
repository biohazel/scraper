from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/scrape", status_code=200)
def scrape(url: Optional[str] = None):
    """
    Exemplo de endpoint:
      GET /scrape?url=https://makeone.com.br/blog/
    Retorna um array JSON de posts.

    IMPORTANTE: 'verify=False' ignora checks de certificado TLS.
                Usar apenas como POC. Não recomendado em produção.
    """
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

    # 2. Se for 202, vamos tentar cloudscraper, com verify=False
    if resp.status_code == 202:
        try:
            scraper = cloudscraper.create_scraper()
            # Aqui forçamos verify=False
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed with cloudscraper: {e}"
            )

    # 3. Se ainda não for 200, retornamos erro
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Request returned {resp.status_code}"
        )

    # 4. Parse do HTML via BeautifulSoup
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

    return JSONResponse(content=posts, status_code=200)
