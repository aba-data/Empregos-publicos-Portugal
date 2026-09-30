import json
from playwright.sync_api import sync_playwright
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_reais = []

print("A iniciar o Navegador Fantasma...")

with sync_playwright() as p:
    # Abre o navegador invisível
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        print("A visitar a Infraestruturas de Portugal...")
        # Vai ao site real da IP
        page.goto("https://www.infraestruturasdeportugal.pt/pt-pt/ip/recursos-humanos/recrutamento", timeout=30000)
        
        # Espera 3 segundos para dar tempo ao site de mostrar tudo
        page.wait_for_timeout(3000)
        
        # Procura todos os links na página
        links = page.query_selector_all("a")
        for link in links:
            texto = link.inner_text().strip()
            # Se o botão/link contiver palavras de cargos típicos:
            if any(palavra in texto for palavra in ["Técnico", "Engenheiro", "Operador", "Chefe", "Especialista"]):
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

# Remover vagas repetidas
vagas_unicas = [dict(t) for t in {tuple(d.items()) for d in vagas_reais}]

# Se hoje não houver vagas abertas com essas palavras, deixamos a nota com a hora
if len(vagas_unicas) == 0:
    vagas_unicas.append({
        "titulo": f"Monitorização ativa. Sem vagas novas hoje. (Visto a: {agora})",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Nacional",
        "url": "https://www.infraestruturasdeportugal.pt/pt-pt/ip/recursos-humanos/recrutamento"
    })

# Guardar os dados para o teu site mostrar
with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_unicas, f, ensure_ascii=False, indent=4)

print(f"Terminado! Extraídas {len(vagas_unicas)} vagas.")
