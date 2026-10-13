import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

locais_conhecidos = [
    "Lisboa", "Porto", "Braga", "Setúbal", "Aveiro", "Faro", "Coimbra", 
    "Leiria", "Santarém", "Viseu", "Viana do Castelo", "Vila Real", 
    "Castelo Branco", "Guarda", "Évora", "Beja", "Bragança", "Portalegre", 
    "Almada", "Entroncamento", "Pinhal Novo", "Nelas", "Zona Sul", "Santa Apolónia"
]

print("A iniciar o Navegador Fantasma com varregura profunda até 20 páginas...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        # Aumentado o ciclo de varregura de 0 até 20 páginas
        for num_pag in range(0, 21):
            url_pagina = f"https://www.infraestruturasdeportugal.pt/pt-pt/carreiras?page={num_pag}"
            print(f"A visitar: {url_pagina}")
            
            page.goto(url_pagina, timeout=30000)
            page.wait_for_timeout(3000)
            
            links = page.query_selector_all("a")
            vagas_encontradas_nesta_pagina = 0
            
            for link in links:
                href = link.get_attribute("href")
                texto = link.inner_text().strip()
                
                if href and len(texto) > 12:
                    lixo_comum = ["política", "contactos", "início", "pesquisar", "termos", "carreiras", "saber mais", "candidatura", "cookies", "privacidade"]
                    if any(lixo in texto.lower() for lixo in lixo_comum):
                        continue
                        
                    if "/carreiras/" in href or "/recrutamento/" in href or "/jobs/" in href or "oportunidade" in href.lower():
                        link_final = href if href.startswith('http') else "https://www.infraestruturasdeportugal.pt" + href
                        
                        texto_limpo = texto.split('\n')[0].strip()
                        distrito = "Nacional / Vários"
                        
                        texto_completo = texto_limpo + " " + link_final
                        locais_encontrados = []
                        for loc in locais_conhecidos:
                            if loc.lower() in texto_completo.lower():
                                locais_encontrados.append(loc)
                        
                        if locais_encontrados:
                            distrito = " / ".join(dict.fromkeys(locais_encontrados))
                        
                        vagas_reais.append({
                            "titulo": texto_limpo,
                            "entidade": "Infraestruturas de Portugal",
                            "distrito": distrito,
                            "url": link_final
                        })
                        vagas_encontradas_nesta_pagina += 1
            
            # Se uma página acima da 0 não trouxer vagas, o site esgotou-se e podemos parar para poupar tempo
            if vagas_encontradas_nesta_pagina == 0 and num_pag > 0:
                print(f"Página {num_pag} vazia. Fim da recolha.")
                break
                
    except Exception as erro:
        print("Aviso ao ler as páginas de carreiras:", erro)
        
    browser.close()

# Remover duplicados exatos por URL
vagas_unicas = []
vistos = set()
for vaga in vagas_reais:
    if vaga['url'] not in vistos:
        vagas_unicas.append(vaga)
        vistos.add(vaga['url'])

if len(vagas_unicas) == 0:
    vagas_unicas.append({
        "titulo": f"Monitorização ativa. Nenhuma vaga encontrada. (Visto a: {agora})",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Nacional",
        "url": "https://www.infraestruturasdeportugal.pt/pt-pt/carreiras"
    })

with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_unicas, f, ensure_ascii=False, indent=4)

print(f"Sucesso! Extraídas {len(vagas_unicas)} vagas das 20 páginas analisadas.")
