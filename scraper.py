import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

# Lista exaustiva de TODOS os distritos de Portugal e principais regiões operacionais
locais_conhecidos = [
    "Lisboa", "Porto", "Braga", "Setúbal", "Aveiro", "Faro", "Coimbra", 
    "Leiria", "Santarém", "Viseu", "Viana do Castelo", "Vila Real", 
    "Castelo Branco", "Guarda", "Évora", "Beja", "Bragança", "Portalegre",
    "Almada", "Entroncamento", "Pinhal Novo", "Nelas", "Zona Sul", "Zona Norte", 
    "Zona Centro", "Santa Apolónia", "Campanhã", "Alentejo", "Algarve"
]

print("A iniciar o Navegador Fantasma com cobertura total de distritos...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        url_base = "https://recrutamento.infraestruturasdeportugal.pt/jobs"
        print(f"A aceder a {url_base}...")
        
        page.goto(url_base, timeout=30000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        # Descer a página para carregar todos os elementos dinâmicos
        for i in range(8):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
        
        elementos = page.query_selector_all("a[href*='/jobs/']")
        print(f"Total de links brutos encontrados: {len(elementos)}")
        
        for el in elementos:
            try:
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
                            # Procura insensível a maiúsculas/minúsculas por cada distrito na string completa
                            if re.search(r'\b' + re.escape(loc) + r'\b', texto_completo, re.IGNORECASE):
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
            except Exception as e:
                continue
                
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

print(f"Sucesso! Extraídas {len(vagas_unicas)} vagas com cobertura nacional total.")
