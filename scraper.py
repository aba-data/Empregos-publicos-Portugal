import json
import requests
from datetime import datetime

agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
vagas_finais = []

# Em vez de ler HTML frágil, vamos ligar-nos diretamente a uma Base de Dados (API) pública
url_api = "https://remotive.com/api/remote-jobs?category=software-dev&limit=15"

try:
    # 1. Fazemos o pedido diretamente à API
    resposta = requests.get(url_api, timeout=10)
    dados = resposta.json() # Convertemos imediatamente a resposta para dados estruturados
    
    # 2. Por cada vaga real que a API nos devolveu, guardamos no nosso formato
    for vaga in dados.get("jobs", []):
        vagas_finais.append({
            "titulo": vaga.get("title", "Vaga sem título"),
            "entidade": vaga.get("company_name", "Empresa Confidencial"),
            "distrito": vaga.get("candidate_required_location", "Nacional"),
            "url": vaga.get("url", "#")
        })
        
except Exception as erro:
    print("Erro ao ler a API:", erro)

# Se a API falhar, deixamos a mensagem
if len(vagas_finais) == 0:
    vagas_finais.append({
        "titulo": f"Sem ligação à base de dados. (Visto a: {agora})",
        "entidade": "Sistema",
        "distrito": "Nacional",
        "url": "#"
    })

# Guardar no ficheiro do teu site
with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(vagas_finais, f, ensure_ascii=False, indent=4)

print(f"Robô terminou! Extraiu {len(vagas_finais)} vagas de forma limpa via API.")
