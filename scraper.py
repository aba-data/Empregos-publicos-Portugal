import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

# Lista de segurança de locais para garantir que nunca falha
locais_conhecidos = [
    "Lisboa", "Porto", "Braga", "Setúbal", "Aveiro", "Faro", "Coimbra", 
    "Leiria", "Santarém", "Viseu", "Viana do Castelo", "Vila Real", 
    "Castelo Branco", "Guarda", "Évora", "Beja", "Bragança", "Portalegre", 
    "Almada", "Entroncamento", "Pinhal Novo", "Nelas", "Santa Apolónia"
]

print("A iniciar o Navegador Fantasma...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        page.goto("https://recrutamento.infraestruturasdeportugal.pt/jobs", timeout=30000)
        page.wait_for_timeout(3000)
        
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href")
            texto = link.inner_text().strip()
            
            if href and "/jobs/" in href and len(texto) > 8:
                if href != "/jobs" and href != "https://recrutamento.infraestruturasdeportugal.pt/jobs":
                    
                    link_final = href if not href.startswith('/') else "https://recrutamento.infraestruturasdeportugal.pt" + href
                    texto_limpo = texto.split('\n')[0].strip()
                    distrito_final = "Nacional / Vários"
                    
                    # O TRUQUE MÁGICO: Cortar pela sigla (M/F)
                    if "(M/F)" in texto_limpo.upper():
                        # Divide a frase em duas partes: antes e depois do (M/F)
                        partes = re.split(r'\(M/F\)', texto_limpo, flags=re.IGNORECASE)
                        
                        if len(partes) > 1 and len(partes[1].strip()) > 2:
                            # Apanha a morada, limpando os traços chatos e espaços
                            distrito_final = partes[1].replace('-', '').replace('–', '').strip()
                            # Reconstrói o título só com a profissão
                            texto_limpo = partes[0].strip() + " (M/F)"
                    else:
                        # Se por acaso não tiver (M/F), tenta procurar pelas cidades na nossa lista
                        for local in locais_conhecidos:
                            if local.upper() in texto_limpo.upper():
                                distrito_final = local
                                break

                    # Prevenir que o distrito fique gigante caso algo corra mal
                    if len(distrito_final) > 35:
                        distrito_final = "Vários Locais"
                    
                    vagas_reais.append({
                        "titulo": texto_limpo,
                        "entidade": "Infraestruturas de Portugal",
                        "distrito": distrito_final,
                        "url": link_final
                    })
    except Exception as erro:
        print("Aviso ao ler vagas:", erro)
        
    browser.close()

# Remover repetidos
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

print(f"Sucesso! Extraídas {len(vagas_unicas)} vagas.")
