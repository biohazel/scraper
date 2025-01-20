from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape():
    # Pega a URL via query param (ex: /scrape?url=https://makeone.com.br/blog/)
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    # Faz o GET da página
    resp = requests.get(url)
    html = resp.text

    # Faz o parse com BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Exemplo: extrair posts do blog MakeOne
    posts = []
    for article in soup.select('article.elementor-post'):
        title_elem = article.select_one('.elementor-post__title a')
        date_elem = article.select_one('.elementor-post-date')
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

    return jsonify(posts)

if __name__ == "__main__":
    app.run(debug=True)

