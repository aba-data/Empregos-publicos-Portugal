import json
from datetime import datetime

# 1. Que horas são agora?
agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

# 2. Criar uma vaga de teste com a hora atual para veres o robô a funcionar
novas_vagas = [
    {
        "titulo": "Técnico de Operações (Atualizado: " + agora + ")",
        "entidade": "Infraestruturas de Portugal",
        "distrito": "Lisboa",
        "url": "https://www.infraestruturasdeportugal.pt/"
    },
    {
        "titulo": "Inspetor de Linha",
        "entidade": "Comboios de Portugal (CP)",
        "distrito": "Nacional",
        "url": "https://www.cp.pt/"
    }
]

# 3. Guardar tudo no ficheiro vagas.json
with open('vagas.json', 'w', encoding='utf-8') as f:
    json.dump(novas_vagas, f, ensure_ascii=False, indent=4)

print("Robô terminou com sucesso! Vagas atualizadas.")
