
import json
import re
import unicodedata
import urllib.request
from urllib.parse import urljoin, urlparse, urlunparse
from playwright.sync_api import sync_playwright

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_IP = "https://recrutamento.infraestruturasdeportugal.pt"
URL_LISTA_IP = f"{BASE_IP}/jobs"

URL_LISTA_CP = "https://www.cp.pt/info/ofertas-disponiveis"

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


# Mapa completo de municípios portugueses (inclui municípios fora do
# mapeamento manual). É carregado uma vez por execução; se a fonte estiver
# indisponível, o scraper continua a usar o mapeamento local abaixo.
URL_MUNICIPIOS = "https://raw.githubusercontent.com/JoaoFOliveira/portuguese-municipalities/master/municipalities.json"


def sem_acentos(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    return "".join(caracter for caracter in valor if not unicodedata.combining(caracter)).casefold()


def carregar_municipios_portugal():
    try:
        pedido = urllib.request.Request(
            URL_MUNICIPIOS,
            headers={"User-Agent": "Empregos-publicos-Portugal/1.0"},
        )
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        carregados = {}
        if isinstance(dados, list):
            for item in dados:
                if not isinstance(item, dict):
                    continue
                nome = item.get("name") or item.get("municipality") or item.get("municipio")
                distrito = item.get("district") or item.get("distrito")
                if nome and distrito:
                    carregados[sem_acentos(nome)] = distrito
        if carregados:
            print(f"Geografia: {len(carregados)} municípios carregados automaticamente.")
            return carregados
        print("Geografia: formato da lista de municípios não reconhecido; uso o mapa local.")
    except Exception as erro:
        print(f"Geografia: não foi possível atualizar a lista de municípios ({erro}); uso o mapa local.")
    return {}


MUNICIPIOS_PORTUGAL = carregar_municipios_portugal()

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
    """Identifica distritos através de municípios e localidades mencionados."""
    texto_normalizado = sem_acentos(texto)
    encontrados = []

    # Mapa dinâmico de municípios primeiro; depois, localidades/estações
    # conhecidas no mapa local. Expressões longas têm prioridade para evitar
    # correspondências parciais (por exemplo, Vila Real de Santo António).
    localidades = {}
    localidades.update(MUNICIPIOS_PORTUGAL)
    localidades.update({sem_acentos(k): v for k, v in LOCALIDADES_DISTRITOS.items()})

    for localidade, distrito in sorted(localidades.items(), key=lambda item: len(item[0]), reverse=True):
        if not localidade:
            continue
        padrao = r"(?<![a-z0-9])" + re.escape(localidade) + r"(?![a-z0-9])"
        if re.search(padrao, texto_normalizado):
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
    """Recolhe ofertas da página oficial da CP e visita cada anúncio."""
    vagas = {}
    print("CP: a consultar ofertas disponíveis...")

    page.goto(URL_LISTA_CP, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    # A página pode apresentar os anúncios em cartões ou links institucionais.
    # Recolhemos todos os links e filtramos apenas os de páginas de recrutamento.
    links = page.locator("a[href]").evaluate_all("""
        anchors => anchors.map(a => ({
            titulo: (a.innerText || a.textContent || '').trim(),
            url: a.href,
            contexto: (
                a.closest('article')?.innerText ||
                a.closest('li')?.innerText ||
                a.parentElement?.parentElement?.innerText ||
                a.innerText ||
                ''
            ).trim()
        }))
    """)

    ofertas = {}
    for item in links:
        link = normalizar_url(item.get("url", ""))
        partes = urlparse(link)
        host = (partes.hostname or "").lower()

        if host not in {"cp.pt", "www.cp.pt", "www1.cp.pt", "www2.cp.pt"}:
            continue

        caminho = partes.path.rstrip("/")
        # O formato usado pela CP para anúncios de recrutamento é, por exemplo,
        # /info/w/institucional/revisor-orv. Aceitar páginas desse tipo sem
        # depender do nome específico da oferta.
        if not re.fullmatch(r"/info/w/institucional/[^/]+", caminho, flags=re.I):
            continue
        if caminho.casefold().endswith("/ofertas-disponiveis"):
            continue

        titulo_link = " ".join((item.get("titulo") or "").split())
        contexto = item.get("contexto") or ""
        # Evitar capturar links genéricos de navegação.
        if not titulo_link and not contexto:
            continue
        ofertas[link] = {
            "url": link,
            "titulo_lista": titulo_link,
            "contexto": contexto,
        }

    print(f"CP: {len(ofertas)} links candidatos encontrados na página.")

    # Fallback: a listagem pode carregar os cartões de forma dinâmica e não
    # expor os links no HTML inicial. Estes links oficiais confirmados servem
    # como ponto de partida; a descoberta automática continua a ser tentada acima.
    links_conhecidos_cp = [
        ("Assistente Administrativo - Secretaria-Geral", "https://www.cp.pt/info/w/institucional/assistente-administrativo-secretaria-geral"),
        ("Revisor (ORV)", "https://www.cp.pt/info/w/institucional/revisor-orv"),
        ("Técnico de Manutenção", "https://www.cp.pt/info/w/institucional/tecnico-manutencao"),
    ]
    for titulo_conhecido, url_conhecido in links_conhecidos_cp:
        link = normalizar_url(url_conhecido)
        ofertas.setdefault(link, {
            "url": link,
            "titulo_lista": titulo_conhecido,
            "contexto": titulo_conhecido,
        })

    print(f"CP: {len(ofertas)} links candidatos encontrados (incluindo links oficiais conhecidos).")
    if not ofertas:
        print("CP: não foram encontrados links de detalhe na listagem nem nos links de fallback.")

    for url, item in ofertas.items():
        print(f"CP: a analisar {url}")
        titulo = ""
        texto_pagina = ""

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(500)
            texto_pagina = page.locator("body").inner_text()

            if page.locator("h1").count() > 0:
                titulo = " ".join(page.locator("h1").first.inner_text().split())

            if not titulo or titulo.casefold() in {
                "ofertas disponíveis", "ofertas de emprego", "empregos", "ofertas de emprego"
            }:
                titulo = item["titulo_lista"]

        except Exception as erro:
            print(f"CP: não foi possível ler {url}: {erro}")
            continue

        if not titulo:
            print(f"CP: título não identificado em {url}")
            continue

        # A localização pode surgir como "Local:", "Localizações:" ou em
        # texto corrido, por exemplo "Lisboa-Rossio; Cais do Sodré; Faro".
        localizacao = extrair_localizacoes(texto_pagina)
        if not localizacao:
            localizacao = extrair_localizacoes(item["contexto"])

        texto_para_identificar = " | ".join(
            parte for parte in [localizacao, titulo] if parte
        )
        distritos = identificar_distritos(texto_para_identificar)
        if not distritos:
            distritos = identificar_distritos(texto_pagina)
        if not distritos:
            distritos = ["Nacional / Vários"]

        for distrito in distritos:
            adicionar_vaga(vagas, {
                "titulo": titulo,
                "entidade": "CP - Comboios de Portugal",
                "distrito": distrito,
                "local": localizacao or "Localização por confirmar",
                "url": url,
            })

    print(f"CP: {len(vagas)} registos por distrito recolhidos.")
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
