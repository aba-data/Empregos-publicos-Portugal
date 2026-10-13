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

print("A iniciar o Navegador Fantasma no portal oficial de recrutamento (até 20 páginas)...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        # Varredura profunda pelas páginas do portal de recrutamento real
        for num_pag in range(1, 21):
            url_pagina = f"https://recrutamento.infraestruturasdeportugal.pt/jobs?page={num_pag}"
            print(f"A visitar: {url_pagina}")
            
            page.goto(url_pagina, timeout=30000)
            page.wait_for_timeout(3000)
            
            elementos = page.query_selector_all("a[href*='/jobs/']")
            vagas_encontradas_nesta_pagina = 0
            
            for el in elementos:
                href = el.get_attribute("href")
                texto = el.inner_text().strip()
                
                if href and "/jobs/" in href:
                    if href != "/jobs" and "page=" not in href and "tag=" not in href:
                        
                        link_final = href if not href.startswith('/') else "https://recrutamento.infraestruturasdeportugal.pt" + href
                        
                        linhas = [l.strip() for l in texto.split('\n') if l.strip()]
                        if not linhas:
                            continue
                            
                        titulo_bruto = linhas[0]
                        
                        if any(termo in titulo_bruto.lower() for termo in ["política", "cookies", "carreiras", "início", "contacto"]):
                            continue
                            
                        distrito = "Nacional / Vários"
                        texto_completo = " ".join(linhas) + " " + link_final
                        
                        locais_encontrados = []
                        for loc in locais_conhecidos:
                            if loc.lower() in texto_completo.lower():
                                locais_encontrados.append(loc)
                        
                        if locais_encontrados:
                            distrito = " / ".join(dict.fromkeys(locais_encontrados))
                        
                        if "(M/F)" in titulo_bruto.upper():
                            partes = re.split(r'\(M/F\)', titulo_bruto, flags=re.IGNORECASE)
                            titulo_limpo = partes[0].strip() + " (M/F)"
                        else:
                            titulo_limpo = titulo_bruto

                        vagas_reais.append({
                            "titulo": titulo_limpo,
                            "entidade": "Infraestruturas de Portugal",
                            "distrito": distrito,
                            "url": link_final
                        })
                        vagas_encontradas_nesta_pagina += 1
            
            # Se uma página acima da 1 não trouxer vagas, o site esgotou-se
            if vagas_encontradas_nesta_pagina == 0 and num_pag > 1:
                print(f"Página {num_pag} vazia. Fim da recolha.")
                break
                
    except Exception as erro:
        print("Erro ao processar o portal:", erro)
        
    browser.close()

# Remover duplicados rigorosos por URL
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
        "url": "https://recrutamento.infraestruturasdeportugal.pt/jobs"
    })

with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_unicas, f, ensure_ascii=False, indent=4)

print(f"Sucesso! Extraídas {len(vagas_unicas)} vagas em profundidade.")
