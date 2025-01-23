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

app = FastAPI()

# Configurações globais
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15
SELENIUM_TIMEOUT = 30

@app.get("/scrape")
async def scrape(url: Optional[str] = None):
    """
    Endpoint principal para scraping do AdNews
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    if "adnews.com.br" not in url:
        raise HTTPException(status_code=400, detail="Only adnews.com.br domains are allowed")

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
        
        # Tentativa inicial com requests
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        # Fallback para cloudscraper se necessário
        if response.status_code in [403, 429, 503]:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, headers=headers, timeout=REQUEST_TIMEOUT*2)
        
        if response.status_code != 200:
            return []
            
        return parse_articles(BeautifulSoup(response.text, 'html.parser'))
        
    except Exception as e:
        print(f"Requests error: {str(e)}")
        return []

def scrape_adnews_selenium(url: str):
    """
    Método usando Selenium para JS-rendered content
    """
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.binary_location = "/usr/bin/chromium"

    service = Service(executable_path="/usr/lib/chromium/chromedriver")
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(SELENIUM_TIMEOUT)
        
        driver.get(url)
        
        # Espera dinâmica para conteúdo carregar
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.lista-ultimas, article.elementor-post"))
        )
        
        # Scroll para carregar conteúdo JS
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        return parse_articles(soup)
        
    except TimeoutException:
        print("Timeout waiting for page content")
        return []
    except WebDriverException as e:
        print(f"Selenium error: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()

def parse_articles(soup: BeautifulSoup):
    """
    Analisa o conteúdo HTML e extrai os artigos
    """
    results = []
    
    # Novo seletor para layout atualizado
    articles = soup.select("""
        div.lista-ultimas .card-noticia,
        article.elementor-post,
        div.post-item
    """)
    
    for article in articles:
        try:
            # Extração robusta com fallbacks
            link = article.select_one("a[href]")
            title = article.select_one("h2, h3, .title")
            desc = article.select_one("p, .excerpt, .desc")
            img = article.select_one("img[src]")
            
            if not link or not title:
                continue
                
            result = {
                "title": title.get_text(strip=True),
                "url": link['href'].strip(),
                "description": desc.get_text(strip=True) if desc else "",
                "image": img['src'].strip() if img else ""
            }
            
            # Validação básica de URL
            if result["url"].startswith("http"):
                results.append(result)
                
        except Exception as e:
            print(f"Error parsing article: {str(e)}")
            continue
    
    return results[:20]  # Retorna no máximo 20 resultados