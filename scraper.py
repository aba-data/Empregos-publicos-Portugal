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
    "Almada", "Entroncamento", "Pinhal Novo", "Nelas", "Santa Apolónia"
]

print("A iniciar o Navegador Fantasma com suporte a múltiplas páginas...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        url_base = "https://recrutamento.infraestruturasdeportugal.pt/jobs"
        page.goto(url_base, timeout=30000)
        page.wait_for_timeout(3000)
        
        pagina_atual = 1
        max_paginas = 10 # Limite de segurança para evitar loops infinitos
        
        while pagina_atual <= max_paginas:
            print(f"A ler a página {pagina_atual}...")
            
            links = page.query_selector_all("a")
            for link in links:
                href = link.get_attribute("href")
                texto = link.inner_text().strip()
                
                if href and "/jobs/" in href and len(texto) > 8:
                    if href != "/jobs" and href != "https://recrutamento.infraestruturasdeportugal.pt/jobs":
                        
                        link_final = href if not href.startswith('/') else "https://recrutamento.infraestruturasdeportugal.pt" + href
                        texto_limpo = texto.split('\n')[0].strip()
                        distrito_final = "Nacional / Vários"
                        
                        if "(M/F)" in texto_limpo.upper():
                            partes = re.split(r'\(M/F\)', texto_limpo, flags=re.IGNORECASE)
                            if len(partes) > 1 and len(partes[1].strip()) > 2:
                                distrito_final = partes[1].replace('-', '').replace('–', '').strip()
                                texto_limpo = partes[0].strip() + " (M/F)"
                        else:
                            for local in locais_conhecidos:
                                if local.upper() in texto_limpo.upper():
                                    distrito_final = local
                                    break

                        if len(distrito_final) > 35:
                            distrito_final = "Vários Locais"
                        
                        vagas_reais.append({
                            "titulo": texto_limpo,
                            "entidade": "Infraestruturas de Portugal",
                            "distrito": distrito_final,
                            "url": link_final
                        })
            
            # Tentar encontrar e clicar no botão "Seguinte" (próxima página)
            try:
                # Procura por botões comuns de paginação (setas ou texto de próxima página)
                botao_seguinte = page.query_selector("a[rel='next'], .pagination-next a, li.pagination-next a, button.next")
                if not botao_seguinte:
                    # Alternativa: procurar links que contenham texto de avanço
                    elementos_a = page.query_selector_all("a")
                    for el in elementos_a:
                        txt_el = el.inner_text().lower()
                        if "seguinte" in txt_el or "»" in txt_el or ">" in txt_el:
                            # Verifica se não é o mesmo botão já clicado
                            botao_seguinte = el
                            break
                
                if botao_seguinte and botao_seguinte.is_visible():
                    botao_seguinte.click()
                    page.wait_for_timeout(3000)
                    pagina_atual += 1
                else:
                    # Se não houver botão seguinte, terminamos a paginação
                    break
            except Exception:
                break
                
    except Exception as erro:
        print("Aviso ao ler páginas:", erro)
        
    browser.close()

# Remover duplicados
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

print(f"Sucesso total! Extraídas {len(vagas_unicas)} vagas de todas as páginas.")
