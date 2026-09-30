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
        print("A visitar a VERDADEIRA página de recrutamento da IP...")
        # Vamos à página principal desse portal secreto que descobriste
        page.goto("https://recrutamento.infraestruturasdeportugal.pt/jobs", timeout=30000)
        page.wait_for_timeout(3000)
        
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href")
            texto = link.inner_text().strip()
            
            # A REGRA DE OURO: Só aceitamos links que vão para dentro de "/jobs/" e que tenham texto
            if href and "/jobs/" in href and len(texto) > 8:
                # Ignoramos a própria página de listagem de trabalhos
                if href != "/jobs" and href != "https://recrutamento.infraestruturasdeportugal.pt/jobs":
                    
                    link_final = href
                    if href.startswith('/'):
                        link_final = "https://recrutamento.infraestruturasdeportugal.pt" + href
                        
                    # Como o texto do link às vezes traz a data ou local colados, 
                    # cortamos e apanhamos só a primeira linha (o Título da vaga)
                    titulo_limpo = texto.split('\n')[0]
                    
                    vagas_reais.append({
                        "titulo": titulo_limpo,
                        "entidade": "Infraestruturas de Portugal",
                        "distrito": "Nacional / Vários",
                        "url": link_final
                    })
    except Exception as erro:
        print("Aviso ao ler vagas:", erro)
        
    browser.close()

# O truque mágico para limpar vagas que apareçam repetidas na página
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

print(f"Sucesso total! Extraídas {len(vagas_unicas)} vagas perfeitas da IP.")
