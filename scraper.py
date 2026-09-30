import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas = []

# 1. O Robô vai ao site real da IP
url = "https://www.infraestruturasdeportugal.pt/pt-pt/ip/recursos-humanos/recrutamento"

# Finge ser um navegador de um computador normal para não ser bloqueado
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    # Pede a página à internet e lê o código HTML
    resposta = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resposta.text, 'html.parser')
    
    # Procura todos os links na página
    links = soup.find_all('a', href=True)
    
    # Filtra apenas os links que falam de vagas/cargos
    for link in links:
        texto = link.text.strip()
        if "Técnico" in texto or "Engenheiro" in texto or "Operador" in texto or "Chefe" in texto:
            link_final = link['href']
            # Se o link estiver incompleto, junta-lhe o início do site
            if link_final.startswith('/'):
                link_final = "https://www.infraestruturasdeportugal.pt" + link_final
                
            vagas.append({
                "titulo": texto,
                "entidade": "Infraestruturas de Portugal",
                "distrito": "Nacional",
                "url": link_final
            })
except Exception as erro:
    print("Erro ao ler site da IP:", erro)

# Se hoje não houver vagas abertas com essas palavras, deixamos uma mensagem automática
if len(vagas) == 0:
    vagas.append({
        "titulo": "Sem concursos ativos neste momento. (Visto a: " + agora + ")",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Nacional",
        "url": url
    })

# 2. Guardar as vagas reais no ficheiro do teu site
with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas, f, ensure_ascii=False, indent=4)

print(f"Robô terminou! Extraiu {len(vagas)} vagas.")
