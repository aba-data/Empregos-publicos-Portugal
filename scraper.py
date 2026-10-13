import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

print("A iniciar o Navegador Fantasma com escuta de elementos dinâmicos...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        url_base = "https://recrutamento.infraestruturasdeportugal.pt/jobs"
        print(f"A aceder a {url_base}...")
        
        page.goto(url_base, timeout=30000)
        # Dar tempo para o site injetar todo o conteúdo via JavaScript
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)
        
        # Fazer scroll para baixo para garantir que o site carrega tudo se tiver scroll infinito
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        
        # Vamos procurar todos os blocos/cartões ou links que contenham /jobs/
        elementos = page.query_selector_all("a[href*='/jobs/']")
        print(f"Total de links brutos encontrados: {len(elementos)}")
        
        for el in elementos:
            try:
                href = el.get_attribute("href")
                texto = el.inner_text().strip()
                
                # Filtrar apenas links de vagas reais
                if href and "/jobs/" in href:
                    if href != "/jobs" and "page=" not in href and "tag=" not in href:
                        
                        link_final = href if not href.startswith('/') else "https://recrutamento.infraestruturasdeportugal.pt" + href
                        
                        # Limpar o texto recolhido
                        linhas = [l.strip() for l in texto.split('\n') if l.strip()]
                        if not linhas:
                            continue
                            
                        # A primeira linha costuma ser o título da vaga
                        titulo_bruto = linhas[0]
                        
                        # Ignorar lixo de navegação
                        if any(termo in titulo_bruto.lower() for termo in ["política", "cookies", "carreiras", "início", "contacto"]):
                            continue
                            
                        distrito = "Nacional / Vários"
                        
                        # Tentar extrair o distrito do texto do elemento ou do título
                        texto_completo = " ".join(linhas)
                        
                        # Procurar por padrões conhecidos de localização no texto completo
                        locais = ["Lisboa", "Porto", "Braga", "Setúbal", "Aveiro", "Faro", "Coimbra", 
                                  "Leiria", "Santarém", "Viseu", "Viana do Castelo", "Vila Real", 
                                  "Castelo Branco", "Guarda", "Évora", "Beja", "Bragança", "Portalegre", 
                                  "Almada", "Entroncamento", "Pinhal Novo", "Nelas", "Zona Sul", "Santa Apolónia"]
                        
                        for loc in locais:
                            if loc.lower() in texto_completo.lower():
                                distrito = loc
                                break
                        
                        # Se tiver (M/F), limpamos o título para ficar elegante
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

print(f"Extração concluída com sucesso! Total de vagas reais unicas: {len(vagas_unicas)}")
