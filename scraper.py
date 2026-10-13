
import json
import re
from urllib.parse import urljoin, urlparse, urlunparse
from playwright.sync_api import sync_playwright

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_IP = "https://recrutamento.infraestruturasdeportugal.pt"
URL_LISTA_IP = f"{BASE_IP}/jobs"

URL_LISTA_CP = "https://www.cp.pt/info/pt/ofertas-disponiveis"

FICHEIRO_SAIDA = "vagas.json"

# Mapeamento geográfico, não contém ofertas específicas.
# Acrescenta localidades aqui quando necessário.

LOCALIDADES_DISTRITOS = {
    # Lisboa
    "lisboa": "Lisboa",
    "rossio": "Lisboa",
    "cais do sodré": "Lisboa",
    "cais do sodre": "Lisboa",
    "santa apolónia": "Lisboa",
    "santa apolonia": "Lisboa",
    "campolide": "Lisboa",
    "entrecampos": "Lisboa",
    "amadora": "Lisboa",
    "sintra": "Lisboa",
    "cascais": "Lisboa",
    "oeiras": "Lisboa",
    "queluz": "Lisboa",
    "azambuja": "Lisboa",

    # Faro
    "faro": "Faro",
    "tavira": "Faro",
    "olhão": "Faro",
    "olhao": "Faro",
    "loulé": "Faro",
    "loule": "Faro",
    "portimão": "Faro",
    "portimao": "Faro",
    "lagos": "Faro",
    "albufeira": "Faro",
    "vila real de santo antónio": "Faro",
    "vila real de santo antonio": "Faro",

    # Porto
    "porto": "Porto",
    "campanhã": "Porto",
    "campanha": "Porto",
    "são bento": "Porto",
    "sao bento": "Porto",
    "gaia": "Porto",
    "vila nova de gaia": "Porto",
    "ermesinde": "Porto",

    # Outros distritos
    "aveiro": "Aveiro",
    "espinho": "Aveiro",
    "beja": "Beja",
    "braga": "Braga",
    "barcelos": "Braga",
    "bragança": "Bragança",
    "braganca": "Bragança",
    "castelo branco": "Castelo Branco",
    "coimbra": "Coimbra",
    "figueira da foz": "Coimbra",
    "évora": "Évora",
    "evora": "Évora",
    "guarda": "Guarda",
    "leiria": "Leiria",
    "marinha grande": "Leiria",
    "portalegre": "Portalegre",
    "santarém": "Santarém",
    "santarem": "Santarém",
    "entroncamento": "Santarém",
    "tomar": "Santarém",
    "setúbal": "Setúbal",
    "setubal": "Setúbal",
    "barreiro": "Setúbal",
    "pinhal novo": "Setúbal",
    "viseu": "Viseu",
    "viana do castelo": "Viana do Castelo",
    "vila real": "Vila Real",
    "funchal": "Madeira",
    "madeira": "Madeira",
    "ponta delgada": "Açores",
    "açores": "Açores",
    "acores": "Açores",

    # Localidades adicionais frequentes nos anúncios
    "almada": "Setúbal",
    "seixal": "Setúbal",
    "sesimbra": "Setúbal",
    "sines": "Setúbal",
    "montijo": "Setúbal",
    "moita": "Setúbal",
    "alcochete": "Setúbal",
    "palmela": "Setúbal",
    "setubal": "Setúbal",
    "setúbal": "Setúbal",
    "pinhal novo": "Setúbal",
    "caldas da rainha": "Leiria",
    "peniche": "Leiria",
    "óbidos": "Leiria",
    "obidos": "Leiria",
    "torres vedras": "Lisboa",
    "mafra": "Lisboa",
    "loures": "Lisboa",
    "vila franca de xira": "Lisboa",
    "alverca": "Lisboa",
    "alhandra": "Lisboa",
    "santarém": "Santarém",
    "santarem": "Santarém",
    "abrantes": "Santarém",
    "torres novas": "Santarém",
    "castelo branco": "Castelo Branco",
    "fundão": "Castelo Branco",
    "fundao": "Castelo Branco",
    "guimarães": "Braga",
    "guimaraes": "Braga",
    "famalicão": "Braga",
    "famalicao": "Braga",
    "vila nova de famalicão": "Braga",
    "vila nova de famalicao": "Braga",
    "chaves": "Vila Real",
    "peso da régua": "Vila Real",
    "peso da regua": "Vila Real",
    "mirandela": "Bragança",
    "ovar": "Aveiro",
    "ílhavo": "Aveiro",
    "ilhavo": "Aveiro",
    "viseu": "Viseu",
    "lamego": "Viseu",
    "covilhã": "Castelo Branco",
    "covilha": "Castelo Branco",
    "serpa": "Beja",
    "mour a": "Beja",
    "mourão": "Évora",
    "moura": "Beja",
    "elvas": "Portalegre",
    "portalegre": "Portalegre",
    "santiago do cacém": "Setúbal",
    "santiago do cacem": "Setúbal",
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_url(url):
    """Remove fragmentos e parâmetros de tracking."""
    partes = urlparse(url)

    return urlunparse((
        partes.scheme,
        partes.netloc,
        partes.path.rstrip("/"),
        "",
        "",
        "",
    ))


def identificar_distritos(texto):
    """
    Identifica os distritos através das localidades encontradas.
    Devolve uma lista sem duplicados.
    """
    texto = (texto or "").casefold()
    encontrados = []

    # Procurar primeiro as expressões geográficas mais longas.
    localidades = sorted(
        LOCALIDADES_DISTRITOS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for localidade, distrito in localidades:
        padrao = (
            r"(?<![a-záàâãéêíóôõúç])"
            + re.escape(localidade)
            + r"(?![a-záàâãéêíóôõúç])"
        )

        if re.search(padrao, texto):
            if distrito not in encontrados:
                encontrados.append(distrito)

    return encontrados


def extrair_localizacoes(texto):
    """
    Extrai linhas como:
    Local: Lisboa
    Localizações: Lisboa e Faro
    """
    localizacoes = []

    for linha in (texto or "").splitlines():
        linha = linha.strip()

        correspondencia = re.match(
            r"^Local(?:izações)?\s*:\s*(.+)$",
            linha,
            flags=re.IGNORECASE,
        )

        if correspondencia:
            valor = correspondencia.group(1).strip()

            if valor:
                localizacoes.append(valor)

    return " | ".join(dict.fromkeys(localizacoes))


def adicionar_vaga(vagas, vaga):
    """
    Deduplica por entidade, URL e distrito.
    Uma oferta com vários distritos mantém um registo por distrito.
    """
    chave = (
        vaga["entidade"].casefold()
        + "|"
        + normalizar_url(vaga["url"])
        + "|"
        + vaga["distrito"].casefold()
    )

    vagas[chave] = vaga


# ============================================================
# RECOLHA DA INFRAESTRUTURAS DE PORTUGAL
# ============================================================

def recolher_vagas_ip(page):
    """
    Recolhe dinamicamente os anúncios da IP e visita cada anúncio
    para tentar identificar a localização e o(s) distrito(s).
    """
    vagas = {}
    anuncios = {}

    print("IP: a abrir a lista de ofertas...")

    page.goto(
        URL_LISTA_IP + "?page=1",
        wait_until="domcontentloaded",
        timeout=60000,
    )
    page.wait_for_selector("a[href*='/jobs/']", timeout=30000)

    links_paginacao = page.locator(
        "a[href*='page=']"
    ).evaluate_all("(els) => els.map(a => a.href)")

    paginas = [
        int(m.group(1))
        for link in links_paginacao
        if (m := re.search(r"[?&]page=(\d+)", link))
    ]
    ultima_pagina = max(paginas, default=1)

    for numero in range(1, ultima_pagina + 1):
        url = f"{URL_LISTA_IP}?page={numero}"
        print(f"IP: página {numero}/{ultima_pagina}")

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("a[href*='/jobs/']", timeout=30000)

        elementos = page.locator("a[href*='/jobs/']").evaluate_all("""
            els => els.map(a => ({
                titulo: a.innerText.trim(),
                url: a.href
            }))
        """)

        for item in elementos:
            titulo = item["titulo"].splitlines()[0].strip()
            link = normalizar_url(item["url"])

            if not titulo or "/jobs/" not in urlparse(link).path:
                continue
            if titulo.casefold() in {"anterior", "próxima", "proxima", "seguinte"}:
                continue
            if "page=" in link or "tag=" in link:
                continue

            anuncios.setdefault(link, titulo)

    print(f"IP: {len(anuncios)} anúncios únicos encontrados.")

    for url, titulo_lista in anuncios.items():
        print(f"IP: a analisar {titulo_lista}")

        titulo = titulo_lista
        texto_pagina = ""
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(300)
            texto_pagina = page.locator("body").inner_text()

            if page.locator("h1").count() > 0:
                titulo_pagina = page.locator("h1").first.inner_text().strip()
                if titulo_pagina:
                    titulo = titulo_pagina
        except Exception as erro:
            print(f"IP: não foi possível ler os detalhes de {url}: {erro}")

        # Dar prioridade a linhas explicitamente identificadas como local.
        localizacao = extrair_localizacoes(texto_pagina)
        texto_para_identificar = " | ".join(
            parte for parte in [titulo, localizacao] if parte
        )

        # Se os campos explícitos não forem suficientes, analisar o título
        # e o texto da página, que frequentemente indicam cidade/distrito.
        distritos = identificar_distritos(texto_para_identificar)
        if not distritos:
            distritos = identificar_distritos(titulo)
        if not distritos:
            distritos = identificar_distritos(texto_pagina)

        if not distritos:
            distritos = ["Nacional / Vários"]

        for nome_distrito in distritos:
            adicionar_vaga(
                vagas,
                {
                    "titulo": titulo,
                    "entidade": "Infraestruturas de Portugal",
                    "distrito": nome_distrito,
                    "local": localizacao or titulo_lista,
                    "url": url,
                },
            )

    print(f"IP: {len(vagas)} registos por distrito recolhidos.")
    return list(vagas.values())


# ============================================================
# RECOLHA DA CP - DESCOBERTA DINÂMICA
# ============================================================

def recolher_vagas_cp(page):
    vagas = {}

    print("CP: a consultar ofertas disponíveis...")

    page.goto(
        URL_LISTA_CP,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    # Ler os links existentes na página oficial.
    links = page.locator("a[href]").evaluate_all("""
        anchors => anchors.map(a => ({
            titulo: a.innerText.trim(),
            url: a.href,
            contexto: (
                a.closest('article')?.innerText ||
                a.parentElement?.parentElement?.innerText ||
                a.innerText
            ).trim()
        }))
    """)

    ofertas = {}

    for item in links:
        link = normalizar_url(item["url"])
        partes = urlparse(link)

        # Aceitar apenas páginas de detalhe de ofertas
        # institucionais da CP, não menus nem páginas genéricas.
        if partes.hostname not in {
            "www.cp.pt",
            "cp.pt",
        }:
            continue

        if not re.fullmatch(
            r"/info/w/institucional/[^/]+",
            partes.path,
            flags=re.IGNORECASE,
        ):
            continue

        if link == normalizar_url(URL_LISTA_CP):
            continue

        ofertas[link] = {
            "url": link,
            "titulo_lista": item["titulo"],
            "contexto": item["contexto"],
        }

    if not ofertas:
        raise RuntimeError(
            "A CP não devolveu links de ofertas reconhecíveis. "
            "Verificar a estrutura HTML do portal."
        )

    print(f"CP: {len(ofertas)} páginas de oferta descobertas.")

    for url, item in ofertas.items():
        print(f"CP: a analisar {url}")

        titulo = ""
        texto_pagina = ""

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(500)

            texto_pagina = page.locator("body").inner_text()

            # O título principal costuma estar no h1.
            if page.locator("h1").count() > 0:
                titulo = page.locator("h1").first.inner_text().strip()

            # Excluir títulos genéricos do portal.
            if not titulo or titulo.casefold() in {
                "ofertas disponíveis",
                "ofertas de emprego",
                "empregos",
            }:
                titulo = item["titulo_lista"].strip()

        except Exception as erro:
            print(f"CP: não foi possível ler {url}: {erro}")
            continue

        if not titulo:
            print(f"CP: título não identificado em {url}")
            continue

        # Primeiro, procurar a localização na página de detalhe.
        localizacao = extrair_localizacoes(texto_pagina)

        # Alternativa: contexto do cartão na página de listagem.
        if not localizacao:
            localizacao = extrair_localizacoes(item["contexto"])

        distritos = identificar_distritos(localizacao)

        # Se não houver localização reconhecida, manter o anúncio,
        # sem inventar um distrito.
        if not distritos:
            distritos = ["Nacional / Vários"]

        for distrito in distritos:
            adicionar_vaga(
                vagas,
                {
                    "titulo": titulo,
                    "entidade": "CP - Comboios de Portugal",
                    "distrito": distrito,
                    "local": localizacao or "Localização por confirmar",
                    "url": url,
                },
            )

    print(f"CP: {len(vagas)} registos por distrito.")

    return list(vagas.values())


# ============================================================
# EXECUÇÃO E PUBLICAÇÃO DO JSON
# ============================================================

def main():
    todas_as_vagas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            locale="pt-PT",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        try:
            # A falha de uma entidade não impede necessariamente
            # a recolha da outra.
            try:
                todas_as_vagas.extend(recolher_vagas_ip(page))
            except Exception as erro_ip:
                print(f"ERRO IP: {erro_ip}")

            try:
                todas_as_vagas.extend(recolher_vagas_cp(page))
            except Exception as erro_cp:
                print(f"ERRO CP: {erro_cp}")

        finally:
            browser.close()

    # Deduplicação final.
    vagas_finais = {}

    for vaga in todas_as_vagas:
        chave = (
            vaga["entidade"].casefold()
            + "|"
            + normalizar_url(vaga["url"])
            + "|"
            + vaga["distrito"].casefold()
        )
        vagas_finais[chave] = vaga

    lista_final = list(vagas_finais.values())

    # Não substituir o JSON por uma lista vazia se tudo falhar.
    if not lista_final:
        raise RuntimeError(
            "Nenhuma vaga foi recolhida. "
            "O vagas.json existente não será substituído."
        )

    # Escrita apenas depois de concluir a recolha.
    with open(FICHEIRO_SAIDA, "w", encoding="utf-8") as ficheiro:
        json.dump(
            lista_final,
            ficheiro,
            ensure_ascii=False,
            indent=2,
        )

    total_ip = sum(
        1 for vaga in lista_final
        if vaga["entidade"] == "Infraestruturas de Portugal"
    )

    total_cp = sum(
        1 for vaga in lista_final
        if vaga["entidade"] == "CP - Comboios de Portugal"
    )

    print("=" * 45)
    print(f"IP: {total_ip} registos")
    print(f"CP: {total_cp} registos")
    print(f"TOTAL: {len(lista_final)} registos")
    print(f"Ficheiro atualizado: {FICHEIRO_SAIDA}")


if __name__ == "__main__":
    main()
