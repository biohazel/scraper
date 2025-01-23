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

# Configurações Globais
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 25
SELENIUM_TIMEOUT = 45
BASE_URL = "https://adnews.com.br"

@app.get("/scrape")
async def scrape(url: Optional[str] = None):
    """Endpoint principal para scraping"""
    if not url:
        raise HTTPException(status_code=400, detail="URL é obrigatório")
    
    if "adnews.com.br" not in url:
        raise HTTPException(status_code=400, detail="Domínio não permitido")

    # Tentativa 1: Requests + Cloudscraper
    results = scrape_adnews_requests(url)
    
    # Tentativa 2: Fallback para Selenium
    if not results:
        results = scrape_adnews_selenium(url)
    
    return JSONResponse(content=results or [], status_code=200)

def scrape_adnews_requests(url: str):
    """Método tradicional com tratamento de anti-bot"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        # Se bloqueado, usar Cloudscraper
        if response.status_code in [403, 429, 503]:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, headers=headers, timeout=REQUEST_TIMEOUT*2)
        
        return parse_articles(BeautifulSoup(response.text, 'html.parser')) if response.ok else []
    
    except Exception as e:
        print(f"Erro Requests: {str(e)}")
        return []

def scrape_adnews_selenium(url: str):
    """Método Selenium com configurações anti-detecção"""
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.binary_location = "/usr/bin/chromium"
    
    # Configurações avançadas
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(executable_path="/usr/bin/chromedriver")
    driver = None

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": USER_AGENT})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        driver.set_page_load_timeout(SELENIUM_TIMEOUT)
        driver.get(url)
        
        # Espera inteligente + Scroll
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.result"))
        )
        for _ in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(1.2, 2.5))
        
        return parse_articles(BeautifulSoup(driver.page_source, 'html.parser'))
    
    except Exception as e:
        print(f"Erro Selenium: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()

def parse_articles(soup: BeautifulSoup):
    """Parser otimizado para estrutura 2025 do AdNews"""
    results = []
    articles = soup.select("article.result")
    
    for article in articles:
        try:
            # Extração robusta
            title_tag = article.select_one("h2.title a")
            img_tag = article.select_one("img.attachment-full")
            category_tag = article.select_one(".meta-category")
            
            if not title_tag:
                continue
                
            url = title_tag['href'].strip()
            if not url.startswith(('http', '//')):
                url = f"{BASE_URL}{url}"
                
            results.append({
                "title": title_tag.get_text(strip=True),
                "url": url,
                "description": category_tag.get_text(strip=True) if category_tag else "",
                "image": img_tag['src'] if img_tag else ""
            })
            
        except Exception as e:
            print(f"Erro parsing: {str(e)}")
            continue
    
    return results[:15]  # Limite de resultados