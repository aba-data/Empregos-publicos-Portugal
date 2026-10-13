
import json
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE = "https://recrutamento.infraestruturasdeportugal.pt"
URL_LISTA = f"{BASE}/jobs"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        # Começar na primeira página e descobrir a paginação
        page.goto(URL_LISTA + "?page=1", wait_until="domcontentloaded",
                   timeout=60000)
        page.wait_for_selector("a[href*='/jobs/']", timeout=30000)

        links_paginacao = page.locator("a[href*='page=']").evaluate_all(
            "(els) => els.map(a => a.href)"
        )

        paginas = [
            int(m.group(1))
            for link in links_paginacao
            if (m := re.search(r"[?&]page=(\d+)", link))
        ]

        ultima_pagina = max(paginas, default=1)
        vagas = {}

        for numero in range(1, ultima_pagina + 1):
            url = f"{URL_LISTA}?page={numero}"
            print(f"A recolher página {numero}/{ultima_pagina}")

            page.goto(url, wait_until="domcontentloaded",
                      timeout=60000)
            page.wait_for_selector("a[href*='/jobs/']", timeout=30000)

            elementos = page.locator("a[href*='/jobs/']").evaluate_all("""
                els => els.map(a => ({
                    titulo: a.innerText.trim(),
                    url: a.href
                }))
            """)

            for item in elementos:
                titulo = item["titulo"].split("\\n")[0].strip()
                link = item["url"]

                if not titulo or "/jobs/" not in link:
                    continue

                if titulo.lower() in {
                    "anterior", "próxima", "proxima"
                }:
                    continue

                if "page=" in link or "tag=" in link:
                    continue

                vagas[link] = {
                    "titulo": titulo,
                    "entidade": "Infraestruturas de Portugal",
                    "distrito": "Nacional / Vários",
                    "url": link
                }

        if not vagas:
            raise RuntimeError(
                "Não foram encontradas vagas. O ficheiro anterior "
                "será preservado."
            )

        with open("vagas.json", "w", encoding="utf-8") as f:
            json.dump(
                list(vagas.values()), f,
                ensure_ascii=False, indent=2
            )

        print(f"Recolha concluída: {len(vagas)} ofertas.")

    finally:
        browser.close()
