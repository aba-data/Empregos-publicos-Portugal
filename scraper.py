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
        print("A visitar a NOVA página de carreiras da IP...")
        # O LINK CORRETO QUE ENCONTRASTE!
        page.goto("https://www.infraestruturasdeportugal.pt/pt-pt/carreiras", timeout=30000)
        page.wait_for_timeout(3000)
        
        links = page.query_selector_all("a")
        for link in links:
            texto = link.inner_text().strip()
            
            # Ignoramos botões curtos e links de menu, apanhamos os títulos longos das vagas
            lixo_comum = ["política de", "contactos", "início", "pesquisar", "termos", "carreiras", "saber mais", "candidatura"]
            
            if len(texto) > 12 and not any(lixo in texto.lower() for lixo in lixo_comum):
                href = link.get_attribute("href")
                if href and not href.startswith('#'):
                    link_final = "https://www.infraestruturasdeportugal.pt" + href if href.startswith('/') else href
                    vagas_reais.append({
                        "titulo": texto,
                        "entidade": "Infraestruturas de Portugal",
                        "distrito": "Nacional",
                        "url": link_final
                    })
    except Exception as erro:
        print("Aviso ao ler vagas:", erro)
        
    browser.close()

# Limpar possíveis links duplicados
vagas_unicas = [dict(t) for t in {tuple(d.items()) for d in vagas_reais}]

if len(vagas_unicas) == 0:
    vagas_unicas.append({
        "titulo": f"Monitorização ativa. Nenhuma vaga encontrada. (Visto a: {agora})",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Nacional",
        "url": "https://www.infraestruturasdeportugal.pt/pt-pt/carreiras"
    })

with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_unicas, f, ensure_ascii=False, indent=4)

print(f"Terminado! Extraídas {len(vagas_unicas)} vagas da página certa.")
