from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import cloudscraper
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random

app = FastAPI()

# Configurações globais
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 20
SELENIUM_TIMEOUT = 45

@app.get("/scrape")
async def scrape(url: Optional[str] = None):
    """
    Endpoint principal para scraping do AdNews
    """
    if not url:
        raise HTTPException(status_code=400, detail="Parâmetro URL é obrigatório")

    if "adnews.com.br" not in url:
        raise HTTPException(status_code=400, detail="Somente domínios adnews.com.br são permitidos")

    # Primeira tentativa com requests/cloudscraper
    results = scrape_adnews_requests(url)
    
    # Fallback para Selenium se necessário
    if not results:
        results = scrape_adnews_selenium(url)
    
    return JSONResponse(content=results if results else [], status_code=200)

def scrape_adnews_requests(url: str):
    """
    Método usando Requests + Cloudscraper
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [403, 429, 503]:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, headers=headers, timeout=REQUEST_TIMEOUT*2)
        
        if response.status_code != 200:
            return []
            
        return parse_articles(BeautifulSoup(response.text, 'html.parser'))
        
    except Exception as e:
        print(f"Erro no Requests: {str(e)}")
        return []

def scrape_adnews_selenium(url: str):
    """
    Método usando Selenium com configurações otimizadas
    """
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--single-process")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.binary_location = "/usr/bin/chromium"

    service = Service(executable_path="/usr/bin/chromedriver")
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(SELENIUM_TIMEOUT)
        
        driver.get(url)
        
        # Espera dinâmica com scroll
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.result"))
        )
        
        # Scroll para carregar conteúdo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(1.5, 3.0))
        
        return parse_articles(BeautifulSoup(driver.page_source, 'html.parser'))
        
    except TimeoutException:
        print("Timeout: Conteúdo não carregado")
        return []
    except WebDriverException as e:
        print(f"Erro no Selenium: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()

def parse_articles(soup: BeautifulSoup):
    """
    Analisa o HTML para extrair artigos da busca
    """
    results = []
    articles = soup.select("article.result")
    
    for article in articles:
        try:
            # Extração robusta com fallbacks
            link_tag = article.select_one("h2.title a")
            title_tag = link_tag.text.strip() if link_tag else None
            img_tag = article.select_one("img.attachment-full")
            desc_tag = article.select_one(".meta-category")
            
            if not title_tag:
                continue

            url = link_tag['href'].strip()
            if not url.startswith("http"):
                url = f"https://adnews.com.br{url}"
                
            results.append({
                "title": title_tag,
                "url": url,
                "description": desc_tag.text.strip() if desc_tag else "Sem descrição",
                "image": img_tag['src'] if img_tag else ""
            })
            
        except Exception as e:
            print(f"Erro processando artigo: {str(e)}")
            continue
    
    return results[:20]  # Limita resultados
