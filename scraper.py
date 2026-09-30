import json
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

print("A iniciar o Navegador Fantasma...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        print("A visitar a Infraestruturas de Portugal...")
        page.goto("https://www.infraestruturasdeportugal.pt/pt-pt/ip/recursos-humanos/recrutamento", timeout=30000)
        page.wait_for_timeout(3000)
        
        links = page.query_selector_all("a")
        for link in links:
            texto = link.inner_text().strip()
            
            # Apanha TUDO o que for um link com texto suficientemente longo para ser uma vaga
            # e ignora links de lixo típicos dos menus do site.
            lixo_comum = ["política de privacidade", "contactos", "início", "pesquisar", "termos", "infraestruturas"]
            
            if len(texto) > 10 and not any(lixo in texto.lower() for lixo in lixo_comum):
                href = link.get_attribute("href")
                if href:
                    link_final = "https://www.infraestruturasdeportugal.pt" + href if href.startswith('/') else href
                    vagas_reais.append({
                        "titulo": texto,
                        "entidade": "Infraestruturas de Portugal",
                        "distrito": "Nacional",
                        "url": link_final
                    })
    except Exception as erro:
        print("Aviso ao ler a IP:", erro)
        
    browser.close()

vagas_unicas = [dict(t) for t in {tuple(d.items()) for d in vagas_reais}]

if len(vagas_unicas) == 0:
    vagas_unicas.append({
        "titulo": f"Monitorização ativa. Nenhuma vaga publicada. (Visto a: {agora})",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Nacional",
        "url": "https://www.infraestruturasdeportugal.pt/pt-pt/ip/recursos-humanos/recrutamento"
    })

with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_unicas, f, ensure_ascii=False, indent=4)

print(f"Terminado! Extraídas {len(vagas_unicas)} vagas.")
