from fastapi import FastAPI, HTTPException, Request
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/scrape")
def scrape(url: Optional[str] = None):
    """
    Exemplo de endpoint:
      GET /scrape?url=https://makeone.com.br/blog/
    Retorna um array JSON de posts.
    """
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    # Faz a requisição HTTP
    resp = requests.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to GET {url}")

    html = resp.text

    # Parse do HTML via BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Extrair posts do blog MakeOne (ajuste conforme necessidade)
    posts = []
    for article in soup.select('article.elementor-post'):
        title_elem = article.select_one('.elementor-post__title a')
        date_elem  = article.select_one('.elementor-post-date')
        excerpt_elem = article.select_one('.elementor-post__excerpt p')

        title = title_elem.text.strip() if title_elem else ''
        link = title_elem['href'] if title_elem else ''
        date = date_elem.text.strip() if date_elem else ''
        excerpt = excerpt_elem.text.strip() if excerpt_elem else ''

        posts.append({
            "title": title,
            "link": link,
            "date": date,
            "excerpt": excerpt
        })

    return posts

