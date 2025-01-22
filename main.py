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
    Exemplo de chamada:
      GET /scrape?url=https://adnews.com.br/
      GET /scrape?url=https://adnews.com.br/?s=inteligencia+artificial

    Retorna um JSON array de notícias (title, url, description, image).
    """

    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    # 1. Primeira tentativa com requests
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to GET {url} ({e})"
        )

    # 2. Fallback com cloudscraper se status = 202, 403 ou 503
    if resp.status_code in [202, 403, 503]:
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20, verify=False)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed with cloudscraper: {e}"
            )

    # 3. Verifica status final
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Request returned {resp.status_code}"
        )

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # ------------------------------------------------------------------
    # 4.1. Primeiro seletor (Home do AdNews):
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
    # 4.2. Se não encontrou nada, tenta layout de busca:
    #     "section.elementor-section div.elementor-post"
    #
    # Observação: em páginas de busca AdNews, cada post pode ter
    # <article class="elementor-post ...">
    # ou "div.elementor-post__card" etc.
    # ------------------------------------------------------------------
    if not results:
        articles_search = soup.select("section.elementor-section div.elementor-post")

        for post in articles_search:
            link_tag = post.select_one("a.elementor-post__thumbnail__link, a.elementor-post__read-more, a.elementor-post__title__link")
            # tentamos várias classes que podem surgir
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

    # Se ainda não encontrou nada, pode ser que o layout tenha mudado
    # ou é outra URL que não bate com os seletores acima.
    if not results:
        print("Nenhum resultado encontrado com os seletores conhecidos.")
        # Você pode retornar um array vazio mesmo assim:
        return JSONResponse(content=[], status_code=200)

    # 5. Retorno final
    return JSONResponse(content=results, status_code=200)
