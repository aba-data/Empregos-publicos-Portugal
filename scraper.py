import json
import re
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse, urlunparse
from playwright.sync_api import sync_playwright

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_IP = "https://recrutamento.infraestruturasdeportugal.pt"
URL_LISTA_IP = f"{BASE_IP}/jobs"

URL_LISTA_CP = "https://www.cp.pt/info/ofertas-disponiveis"
URL_LISTA_ADA = "https://www.aguasdoalgarve.pt/content/recrutamento"
URL_LISTA_ULS_ALGARVE = "https://www.ulsalg.min-saude.pt/concursos/?subcategory=0&year_filter=&status=active"

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


MESES_PORTUGUESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

# Datas de prazo aceites: 22/10/2026, 22-10-26, 2026-10-22,
# ou 22 de outubro de 2026.
PADRAO_DATA = re.compile(
    r"\b(?:"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\s+de\s+[A-Za-zÀ-ÿ]+\s+de\s+\d{4}"
    r")\b",
    flags=re.IGNORECASE,
)


def data_consulta_portal():
    """Devolve a data local de Portugal continental no momento da consulta."""
    try:
        return datetime.now(ZoneInfo("Europe/Lisbon")).date()
    except Exception:
        # Compatibilidade caso o ambiente não tenha a base de fusos horários.
        return datetime.now().date()


def converter_data_prazo(valor):
    """Converte uma data de prazo conhecida para date; devolve None se não reconhecer."""
    valor = " ".join((valor or "").strip().split())
    if not valor:
        return None

    # ISO: AAAA-MM-DD
    correspondencia = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", valor)
    if correspondencia:
        try:
            return date(int(correspondencia.group(1)), int(correspondencia.group(2)), int(correspondencia.group(3)))
        except ValueError:
            return None

    # Formato numérico português: DD/MM/AAAA, DD-MM-AA ou DD.MM.AAAA.
    correspondencia = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", valor)
    if correspondencia:
        dia, mes, ano = map(int, correspondencia.groups())
        if ano < 100:
            ano += 2000 if ano < 70 else 1900
        try:
            return date(ano, mes, dia)
        except ValueError:
            return None

    # Formato textual: 22 de outubro de 2026.
    correspondencia = re.fullmatch(
        r"(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)\s+de\s+(\d{4})",
        valor,
        flags=re.IGNORECASE,
    )
    if correspondencia:
        dia = int(correspondencia.group(1))
        mes_texto = sem_acentos(correspondencia.group(2))
        ano = int(correspondencia.group(3))
        mes = MESES_PORTUGUESES.get(mes_texto)
        if mes:
            try:
                return date(ano, mes, dia)
            except ValueError:
                return None
    return None


def extrair_prazo_candidatura(texto):
    """Extrai apenas datas associadas explicitamente ao prazo de candidatura.

    Não confunde a data de publicação do anúncio com a data limite.
    """
    if not texto:
        return None

    # Cada linha/frase é analisada separadamente para evitar associar por engano
    # a data de publicação (normalmente no topo do anúncio) ao prazo final.
    linhas = re.split(r"[\r\n]+|(?<=[.!?])\s+", str(texto))
    padroes_prazo = [
        re.compile(r"prazo.{0,100}candidatur", re.IGNORECASE),
        re.compile(r"data\s+limite.{0,100}candidatur", re.IGNORECASE),
        re.compile(r"candidaturas?.{0,220}\b(?:at[eé]|terminam|terminar|submeter).{0,40}", re.IGNORECASE),
        re.compile(r"ser[aã]o\s+consideradas?.{0,220}\bcandidaturas?", re.IGNORECASE),
    ]

    for linha in linhas:
        linha_limpa = " ".join(linha.split())
        if not linha_limpa or not PADRAO_DATA.search(linha_limpa):
            continue
        if not any(padrao.search(linha_limpa) for padrao in padroes_prazo):
            continue

        for correspondencia_data in PADRAO_DATA.finditer(linha_limpa):
            data_encontrada = converter_data_prazo(correspondencia_data.group(0))
            if data_encontrada:
                return data_encontrada
    return None


def prazo_candidatura_vigente(prazo, data_referencia=None):
    """Filtra prazos vencidos; o próprio dia limite continua válido.

    Se a origem não fornecer uma data de prazo reconhecível, mantém-se a vaga
    quando a página fonte a apresenta como disponível/ativa. Assim, não se
    inventam prazos para as entidades que não os publicam na listagem.
    """
    data_referencia = data_referencia or data_consulta_portal()
    texto = sem_acentos(str(prazo or "").strip())

    if any(termo in texto for termo in ("fechado", "encerrado", "expirado", "fora de prazo")):
        return False

    data_limite = prazo if isinstance(prazo, date) else converter_data_prazo(str(prazo or ""))
    if data_limite is None:
        return True
    return data_limite >= data_referencia


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

def recolher_vagas_ip(page, data_referencia=None):
    """
    Recolhe dinamicamente os anúncios da IP e visita cada anúncio
    para tentar identificar a localização e o(s) distrito(s).
    """
    vagas = {}
    anuncios = {}
    data_referencia = data_referencia or data_consulta_portal()

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

        # Se o anúncio indicar uma data limite de candidatura, excluir o anúncio
        # quando essa data já passou. A lista da IP também pode não apresentar
        # prazo explícito; nesses casos, confiamos na listagem oficial de ofertas.
        data_limite = extrair_prazo_candidatura(texto_pagina)
        if data_limite and data_limite < data_referencia:
            print(f"IP: oferta excluída por prazo vencido ({data_limite.isoformat()}): {titulo}")
            continue

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
                    **({"prazo_candidatura": data_limite.isoformat()} if data_limite else {}),
                },
            )

    print(f"IP: {len(vagas)} registos por distrito recolhidos.")
    return list(vagas.values())


# ============================================================
# RECOLHA DA CP - DESCOBERTA DINÂMICA
# ============================================================

def recolher_vagas_cp(page, data_referencia=None):
    """Recolhe ofertas da página oficial da CP e visita cada anúncio."""
    vagas = {}
    data_referencia = data_referencia or data_consulta_portal()
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

        # Extrai o prazo indicado na candidatura, sem confundir com a data de
        # publicação que pode aparecer no cabeçalho da página.
        data_limite = extrair_prazo_candidatura(texto_pagina)
        if data_limite is None:
            data_limite = extrair_prazo_candidatura(item.get("contexto", ""))
        if data_limite and data_limite < data_referencia:
            print(f"CP: oferta excluída por prazo vencido ({data_limite.isoformat()}): {titulo}")
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
                **({"prazo_candidatura": data_limite.isoformat()} if data_limite else {}),
            })

    print(f"CP: {len(vagas)} registos por distrito recolhidos.")
    return list(vagas.values())


# ============================================================
# RECOLHA DA ÁGUAS DO ALGARVE (GRUPO ÁGUAS DE PORTUGAL)
# ============================================================

def recolher_vagas_aguas_algarve(page, data_referencia=None):
    """Recolhe as ofertas da tabela da Águas do Algarve, ignorando as fechadas."""
    vagas = {}
    data_referencia = data_referencia or data_consulta_portal()
    print("Águas do Algarve: a consultar ofertas de recrutamento...")

    page.goto(URL_LISTA_ADA, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(800)

    linhas = page.locator("table tr").evaluate_all(r"""
        rows => rows.map(tr => Array.from(tr.querySelectorAll('th, td')).map(celula => {
            const link = celula.querySelector('a[href]');
            return {
                texto: (celula.innerText || celula.textContent || '').replace(/\s+/g, ' ').trim(),
                url: link ? link.href : ''
            };
        })).filter(celulas => celulas.length >= 3)
    """)

    if not linhas:
        print("Águas do Algarve: não foi encontrada uma tabela com pelo menos três colunas.")
        return []

    # A tabela oficial apresenta LOCAL DE TRABALHO, CARGO e PRAZO CANDIDATURA.
    # Detetar os índices pelos cabeçalhos evita depender totalmente da sua ordem.
    indices = {"local": 0, "cargo": 1, "prazo": 2}
    primeira = [sem_acentos(c.get("texto", "")) for c in linhas[0]]
    if any("local de trabalho" in valor for valor in primeira):
        for i, valor in enumerate(primeira):
            if "local de trabalho" in valor:
                indices["local"] = i
            elif valor.strip() == "cargo":
                indices["cargo"] = i
            elif "prazo" in valor and "candidatura" in valor:
                indices["prazo"] = i
        linhas = linhas[1:]

    for celulas in linhas:
        try:
            local = celulas[indices["local"]].get("texto", "").strip()
            titulo = celulas[indices["cargo"]].get("texto", "").strip()
            prazo = celulas[indices["prazo"]].get("texto", "").strip()
        except (IndexError, TypeError):
            continue

        if not local or not titulo:
            continue

        # Filtrar por estado e pela data limite. O prazo vale até ao final
        # do próprio dia; a partir do dia seguinte a oferta deixa de ser publicada.
        if not prazo_candidatura_vigente(prazo, data_referencia):
            print(f"Águas do Algarve: oferta excluída por prazo vencido/fechado ({prazo}): {titulo}")
            continue
        data_limite = converter_data_prazo(prazo)

        # O link do anúncio costuma estar na célula do prazo. Procurar em toda a
        # linha também permite lidar com alterações na disposição da tabela.
        url = next(
            (celula.get("url", "").strip() for celula in celulas if celula.get("url", "").strip()),
            URL_LISTA_ADA,
        )

        distritos = identificar_distritos(local)
        if not distritos:
            distritos = ["Faro"] if "algarve" in sem_acentos(local) else ["Nacional / Vários"]

        for distrito in distritos:
            adicionar_vaga(vagas, {
                "titulo": titulo,
                "entidade": "Águas do Algarve (Grupo Águas de Portugal)",
                "distrito": distrito,
                "local": local,
                "url": url,
                "prazo_candidatura": prazo,
                **({"data_limite_candidatura": data_limite.isoformat()} if data_limite else {}),
            })

    print(f"Águas do Algarve: {len(vagas)} vagas abertas recolhidas.")
    return list(vagas.values())


# ============================================================
# RECOLHA DA UNIDADE LOCAL DE SAÚDE DO ALGARVE
# ============================================================

ULS_NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1,
    "dois": 2, "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14, "quatorze": 14,
    "quinze": 15,
    "dezasseis": 16, "dezesseis": 16,
    "dezassete": 17, "dezessete": 17,
    "dezoito": 18,
    "dezanove": 19, "dezenove": 19,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
}


def _numero_portugues(valor):
    """Converte números em algarismos ou escritos por extenso, para prazos da ULS."""
    valor = sem_acentos(str(valor or "").strip()).lower()
    if valor.isdigit():
        return int(valor)
    if valor in ULS_NUMEROS_POR_EXTENSO:
        return ULS_NUMEROS_POR_EXTENSO[valor]
    if " e " in valor:
        partes = valor.split(" e ", 1)
        base = ULS_NUMEROS_POR_EXTENSO.get(partes[0])
        unidade = ULS_NUMEROS_POR_EXTENSO.get(partes[1])
        if base is not None and unidade is not None and base >= 20 and unidade < 10:
            return base + unidade
    return None


def _feriados_nacionais_portugal(ano):
    """Feriados nacionais fixos e móveis relevantes para contar dias úteis."""
    feriados = {
        date(ano, 1, 1),
        date(ano, 4, 25),
        date(ano, 5, 1),
        date(ano, 6, 10),
        date(ano, 8, 15),
        date(ano, 10, 5),
        date(ano, 11, 1),
        date(ano, 12, 1),
        date(ano, 12, 8),
        date(ano, 12, 25),
    }

    # Algoritmo gregoriano para obter o Domingo de Páscoa.
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    pascoa = date(ano, mes, dia)
    feriados.add(pascoa - timedelta(days=2))  # Sexta-feira Santa
    feriados.add(pascoa + timedelta(days=60))  # Corpo de Deus
    return feriados


def _somar_dias_uteis_uls(data_publicacao, numero_dias):
    """Conta dias úteis a partir do dia seguinte à publicação, excluindo feriados nacionais."""
    data_atual = data_publicacao
    contados = 0
    feriados_cache = {}
    while contados < numero_dias:
        data_atual += timedelta(days=1)
        feriados = feriados_cache.setdefault(
            data_atual.year, _feriados_nacionais_portugal(data_atual.year)
        )
        if data_atual.weekday() < 5 and data_atual not in feriados:
            contados += 1
    return data_atual


def _extrair_data_publicacao_uls(texto):
    """Extrai a data do campo de publicação do site, não datas citadas no aviso.

    Importante: o corpo dos avisos também contém expressões como
    "publicado no Boletim ... de 22/06/2018". Essas datas não são a data em
    que o concurso foi publicado no portal e nunca devem ser usadas para
    calcular o prazo de candidatura.
    """
    if not texto:
        return None

    linhas = [" ".join(linha.split()) for linha in str(texto).splitlines() if linha.strip()]
    padrao_campo_publicacao = re.compile(
        r"^\s*(?:data\s+de\s+publica[cç][aã]o|publicado|publicada)\s*:\s*(.*?)\s*$",
        re.IGNORECASE,
    )

    # Primeiro, aceitar apenas campos explícitos e ancorados no início da linha,
    # como "Publicado: 20 de Outubro de 2026". Não procurar a palavra
    # "publicado" livremente no corpo do anúncio.
    for indice, linha in enumerate(linhas):
        correspondencia_campo = padrao_campo_publicacao.match(linha)
        if not correspondencia_campo:
            continue

        valor_data = correspondencia_campo.group(1).strip()
        if not valor_data and indice + 1 < len(linhas):
            valor_data = linhas[indice + 1]

        for correspondencia_data in PADRAO_DATA.finditer(valor_data):
            data_encontrada = converter_data_prazo(correspondencia_data.group(0))
            if data_encontrada:
                return data_encontrada

    # Fallback: em algumas páginas a extração do texto não preserva a quebra
    # de linha entre o rótulo "Publicado:" e a data.
    texto_corrida = " ".join(str(texto).split())
    padrao_data_publicacao = re.compile(
        r"(?:data\s+de\s+publica[cç][aã]o|publicado|publicada)\s*:?\s*("
        r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
        r"\d{4}-\d{2}-\d{2}|"
        r"\d{1,2}\s+de\s+[A-Za-zÀ-ÿ]+\s+de\s+\d{4})",
        re.IGNORECASE,
    )
    correspondencia = padrao_data_publicacao.search(texto_corrida)
    if correspondencia:
        data_encontrada = converter_data_prazo(correspondencia.group(1))
        if data_encontrada:
            return data_encontrada

    return None


def _extrair_prazo_dias_uls(texto):
    """Extrai a duração do prazo de candidatura, mesmo que o HTML quebre linhas."""
    if not texto:
        return None, None

    # O inner_text() do Playwright pode inserir quebras de linha no meio de um
    # parágrafo (por exemplo entre "dias úteis" e "contados a partir"). Por isso
    # a análise é feita sobre texto normalizado e não por linhas separadas.
    texto_corrida = " ".join(str(texto).split())
    texto_norm = sem_acentos(texto_corrida)
    padrao_duracao = re.compile(
        r"(?P<num1>\d{1,3}|[A-Za-zÀ-ÿ]+(?:\s+e\s+[A-Za-zÀ-ÿ]+)?)"
        r"\s*(?:\(\s*(?P<num2>\d{1,3}|[A-Za-zÀ-ÿ]+(?:\s+e\s+[A-Za-zÀ-ÿ]+)?)\s*\))?"
        r"\s+dias?\s*(?P<tipo>úteis|uteis|corridos|consecutivos|seguidos|naturais)?\b",
        re.IGNORECASE,
    )

    for match in padrao_duracao.finditer(texto_corrida):
        antes = sem_acentos(texto_corrida[max(0, match.start() - 260):match.start()])
        depois = sem_acentos(texto_corrida[match.end():match.end() + 300])
        contexto = antes + " " + depois

        # Excluir durações que se referem à validade da bolsa ou do concurso,
        # não ao prazo para apresentar candidaturas.
        if re.search(r"prazo\s+de\s+validade|validade\s+do\s+(?:procedimento|concurso|aviso|bolsa)", antes[-150:]):
            continue

        ligado_a_candidatura = any(termo in contexto for termo in (
            "candidatura", "candidaturas", "apresentacao de candidatura",
            "contados a partir", "contado a partir", "data da publicacao",
            "formalizacao das candidaturas", "prazo de candidatura",
        ))
        tem_contexto_de_prazo = "prazo" in antes[-150:]
        if not ligado_a_candidatura or not tem_contexto_de_prazo:
            continue

        numero = _numero_portugues(match.group("num1"))
        numero_secundario = _numero_portugues(match.group("num2"))
        if numero is None:
            numero = numero_secundario
        if match.group("num2") and str(match.group("num2")).strip().isdigit():
            numero = int(match.group("num2"))
        if match.group("num1") and str(match.group("num1")).strip().isdigit():
            numero = int(match.group("num1"))
        if numero is None or numero <= 0 or numero > 365:
            continue
        tipo = sem_acentos(match.group("tipo") or "corridos")
        return numero, ("uteis" if tipo == "uteis" else "corridos")

    return None, None


def _extrair_data_limite_explicita_uls(texto):
    """Procura uma data-limite escrita explicitamente no aviso."""
    if not texto:
        return None

    partes = re.split(r"[\r\n]+|(?<=[.!?])\s+", str(texto))
    indicios_limite = re.compile(
        r"\b(?:data\s+limite|prazo.{0,80}(?:termina|terminar|terminar[aá]|at[eé])|"
        r"candidaturas?.{0,160}(?:at[eé]|terminam|terminar|terminar[aá]|encerram-se)|"
        r"at[eé]\s+(?:ao\s+)?dia|ultimo\s+dia\s+para|encerramento\s+das\s+candidaturas)\b",
        re.IGNORECASE,
    )
    for parte in partes:
        parte_limpa = " ".join(parte.split())
        if not indicios_limite.search(parte_limpa):
            continue
        # Não usar como data-limite a data de publicação acompanhada de uma duração.
        if re.search(r"contad[oa]s?\s+a\s+partir\s+da\s+data\s+da\s+publica[cç][aã]o", parte_limpa, re.IGNORECASE):
            continue
        for correspondencia in PADRAO_DATA.finditer(parte_limpa):
            data_encontrada = converter_data_prazo(correspondencia.group(0))
            if data_encontrada:
                return data_encontrada
    return None


def _calcular_data_limite_uls(texto_aviso):
    """Calcula a data-limite do concurso usando a data de publicação da página."""
    data_limite = _extrair_data_limite_explicita_uls(texto_aviso)
    if data_limite:
        return data_limite, "data-limite explícita"

    data_publicacao = _extrair_data_publicacao_uls(texto_aviso)
    numero_dias, tipo_dias = _extrair_prazo_dias_uls(texto_aviso)
    if not data_publicacao or not numero_dias or not tipo_dias:
        return None, "não foi possível determinar a data de publicação e/ou a duração do prazo"

    if tipo_dias == "uteis":
        return _somar_dias_uteis_uls(data_publicacao, numero_dias), f"{numero_dias} dias úteis desde {data_publicacao.isoformat()}"
    return data_publicacao + timedelta(days=numero_dias), f"{numero_dias} dias corridos desde {data_publicacao.isoformat()}"


def recolher_vagas_uls_algarve(page, data_referencia=None):
    """Recolhe apenas concursos ULS em curso e com prazo de candidatura vigente."""
    vagas = {}
    anuncios = {}
    data_referencia = data_referencia or data_consulta_portal()
    print(f"ULS Algarve: a consultar concursos ativos; data de referência {data_referencia.isoformat()}...")

    def ler_pagina_listagem(url_pagina):
        page.goto(url_pagina, wait_until="domcontentloaded", timeout=60000)
        # Aguarda brevemente conteúdo gerado pelo tema WordPress, sem depender
        # de um seletor específico que possa mudar.
        page.wait_for_timeout(1000)
        corpo = page.locator("body").inner_text(timeout=20000)
        elementos = page.locator("a[href]").evaluate_all(r"""
            anchors => anchors.map(a => {
                const limpar = v => (v || '').replace(/\s+/g, ' ').trim();
                const acao = /^(ver detalhes|detalhes|ler mais|saber mais|consultar|ver concurso)$/i;
                const href = a.href || '';
                let titulo = '';
                const heading = a.closest('h1, h2, h3, h4, h5');
                if (heading) titulo = limpar(heading.innerText || heading.textContent || '');
                if (!titulo) titulo = limpar(a.innerText || a.textContent || a.getAttribute('aria-label') || a.title || '');

                let contexto = '';
                let no = a;
                for (let passo = 0; no && passo < 10; passo++, no = no.parentElement) {
                    const textoBruto = no.innerText || no.textContent || '';
                    const texto = limpar(textoBruto);
                    // O cartão da oferta contém normalmente o estado "Em Curso".
                    if (texto.length > 20 && texto.length < 4000 && /em\s+curso/i.test(texto)) {
                        contexto = String(textoBruto).split(/\n+/).map(limpar).filter(Boolean).join('\n');
                        const titulos = Array.from(no.querySelectorAll('h1,h2,h3,h4,h5,[class*=title],[class*=titulo]'))
                            .map(el => limpar(el.innerText || el.textContent || ''))
                            .filter(t => t && !acao.test(t) && !/^em curso$/i.test(t) && t.length <= 240);
                        if (titulos.length) titulo = titulos.sort((x,y) => y.length - x.length)[0];
                        break;
                    }
                }

                // Alguns cartões só ligam o botão "Ver Detalhes" ao anúncio;
                // nesse caso, recuperar o título pelo texto do próprio cartão.
                if (!titulo || acao.test(titulo) || /^em curso$/i.test(titulo)) {
                    const linhas = (contexto || '').split(/\n+/).map(limpar).filter(Boolean);
                    const candidatos = linhas.filter(t =>
                        !acao.test(t) && !/^em curso$/i.test(t) &&
                        !/^(concursos|filtros|área:|ano de publicação:|estado:)/i.test(t) &&
                        t.length <= 240
                    );
                    if (candidatos.length) titulo = candidatos[0];
                }
                return { titulo, url: href, contexto };
            })
        """)
        links = page.locator("a[href]").evaluate_all("els => els.map(a => a.href)")
        return corpo, elementos, links

    def adicionar_elementos(elementos):
        antes = len(anuncios)
        for item in elementos:
            url_original = (item.get("url") or "").strip()
            if not url_original:
                continue
            url = normalizar_url(urljoin(URL_LISTA_ULS_ALGARVE, url_original))
            partes_url = urlparse(url)
            host = (partes_url.hostname or "").lower()
            caminho = partes_url.path.rstrip("/")
            # Aceitar o domínio atual e o antigo, e não depender de uma
            # correspondência exata do número de segmentos do URL.
            dominio_oficial = host.endswith(".min-saude.pt") or host == "min-saude.pt"
            if not dominio_oficial or "/concursos/" not in (caminho + "/").lower():
                continue
            parte_slug = caminho.lower().split("/concursos/", 1)[-1].strip("/")
            if not parte_slug or "/" in parte_slug:
                continue  # ignora a própria listagem e URLs de paginação

            titulo = " ".join((item.get("titulo") or "").split())
            contexto = item.get("contexto", "") or ""
            if not titulo or sem_acentos(titulo) in {"ver detalhes", "detalhes", "ler mais", "saber mais", "consultar"}:
                # Último recurso: tirar o título do texto do cartão.
                linhas = [" ".join(l.split()) for l in contexto.splitlines() if l.strip()]
                candidatos = [
                    l for l in linhas
                    if sem_acentos(l) not in {"em curso", "ver detalhes", "detalhes", "ler mais", "saber mais"}
                    and len(l) <= 240
                    and not sem_acentos(l).startswith(("area:", "ano de publicacao:", "estado:"))
                ]
                titulo = candidatos[0] if candidatos else ""
            if not titulo:
                print(f"ULS Algarve: link de concurso sem título utilizável ignorado: {url}")
                continue
            if re.search(r"\b(anulado|anulada|cancelado|cancelada|revogado|revogada)\b", sem_acentos(titulo)):
                print(f"ULS Algarve: concurso anulado/cancelado ignorado: {titulo}")
                continue

            if url not in anuncios or len(titulo) > len(anuncios[url]["titulo"]):
                anuncios[url] = {"titulo": titulo, "contexto_lista": contexto}
        return len(anuncios) - antes

    # O filtro oficial status=active corresponde à seleção "Em Curso".
    corpo_inicial, elementos_iniciais, links_iniciais = ler_pagina_listagem(URL_LISTA_ULS_ALGARVE)
    novos = adicionar_elementos(elementos_iniciais)
    print(f"ULS Algarve: página inicial: {len(elementos_iniciais)} links analisados, {novos} anúncios novos.")

    # Usar os URLs reais de paginação devolvidos pelo site, evitando adivinhar
    # parâmetros ou combinações de filtros.
    paginas = {}
    for link in links_iniciais:
        m = re.search(r"[?&](pg|page|paged|pagina)=(\d+)", link, re.IGNORECASE)
        if m:
            numero = int(m.group(2))
            if 2 <= numero <= 100:
                paginas[numero] = link
    for numero in sorted(paginas):
        print(f"ULS Algarve: a ler página {numero}...")
        try:
            _, elementos, _ = ler_pagina_listagem(paginas[numero])
            novos = adicionar_elementos(elementos)
            print(f"ULS Algarve: página {numero}: {len(elementos)} links analisados, {novos} anúncios novos.")
        except Exception as erro:
            print(f"ULS Algarve: não foi possível ler a página {numero}: {erro}")

    if not anuncios:
        resumo = " ".join(corpo_inicial.split())[:500]
        print(f"ULS Algarve: 0 anúncios reconhecidos. Texto da listagem: {resumo}")
        raise RuntimeError("A listagem ULS foi carregada, mas não foram reconhecidos links de anúncios; consultar o log do GitHub Actions.")

    print(f"ULS Algarve: {len(anuncios)} concursos únicos encontrados no filtro ativo; a validar prazos...")
    for url, item in anuncios.items():
        titulo_lista = item["titulo"]
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(250)
            texto_aviso = page.locator("body").inner_text(timeout=20000)
        except Exception as erro:
            print(f"ULS Algarve: não foi possível ler o corpo do aviso ({titulo_lista}): {erro}")
            continue

        titulo = titulo_lista
        for seletor in ("h1", "h2", "h3"):
            try:
                cabecalho = page.locator(seletor)
                if cabecalho.count() > 0:
                    texto_cabecalho = " ".join(cabecalho.first.inner_text(timeout=1500).split())
                    if texto_cabecalho and sem_acentos(texto_cabecalho) not in {"concursos", "recrutamento | concursos"}:
                        titulo = texto_cabecalho
                        break
            except Exception:
                pass

        if re.search(r"\b(anulado|anulada|cancelado|cancelada|revogado|revogada)\b", sem_acentos(titulo + " " + texto_aviso[:1500])):
            print(f"ULS Algarve: aviso anulado/cancelado ignorado: {titulo}")
            continue

        data_limite, motivo_calculo = _calcular_data_limite_uls(texto_aviso)
        if data_limite is None:
            print(f"ULS Algarve: aviso excluído porque não foi possível confirmar o prazo ({titulo}): {motivo_calculo}")
            continue
        if data_limite < data_referencia:
            print(f"ULS Algarve: aviso excluído por prazo vencido em {data_limite.isoformat()} ({titulo}; cálculo: {motivo_calculo})")
            continue

        print(f"ULS Algarve: aviso aceite até {data_limite.isoformat()} ({titulo}; cálculo: {motivo_calculo})")
        distritos = identificar_distritos(titulo + " " + texto_aviso[:2500]) or ["Faro"]
        for distrito in distritos:
            adicionar_vaga(vagas, {
                "titulo": titulo,
                "entidade": "Unidade Local de Saúde do Algarve (ULS Algarve)",
                "distrito": distrito,
                "local": "Algarve",
                "url": url,
                "estado": "Em Curso",
                "prazo_candidatura": data_limite.isoformat(),
            })

    print(f"ULS Algarve: {len(vagas)} registos com prazo vigente recolhidos.")
    return list(vagas.values())

# ============================================================
# EXECUÇÃO E PUBLICAÇÃO DO JSON
# ============================================================

def main():
    todas_as_vagas = []
    data_referencia = data_consulta_portal()
    print(f"Data de consulta do portal de empregos: {data_referencia.isoformat()}")

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
                todas_as_vagas.extend(recolher_vagas_ip(page, data_referencia))
            except Exception as erro_ip:
                print(f"ERRO IP: {erro_ip}")

            try:
                todas_as_vagas.extend(recolher_vagas_cp(page, data_referencia))
            except Exception as erro_cp:
                print(f"ERRO CP: {erro_cp}")

            try:
                todas_as_vagas.extend(recolher_vagas_aguas_algarve(page, data_referencia))
            except Exception as erro_ada:
                print(f"ERRO Águas do Algarve: {erro_ada}")

            try:
                todas_as_vagas.extend(recolher_vagas_uls_algarve(page, data_referencia))
            except Exception as erro_uls:
                print(f"ERRO ULS Algarve: {erro_uls}")

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
    # Registar em cada registo a data em que o scraper consultou as fontes.
    for vaga in lista_final:
        vaga["data_consulta"] = data_referencia.isoformat()

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

    total_ada = sum(
        1 for vaga in lista_final
        if vaga["entidade"] == "Águas do Algarve (Grupo Águas de Portugal)"
    )

    total_uls = sum(
        1 for vaga in lista_final
        if vaga["entidade"] == "Unidade Local de Saúde do Algarve (ULS Algarve)"
    )

    print("=" * 45)
    print(f"IP: {total_ip} registos")
    print(f"CP: {total_cp} registos")
    print(f"Águas do Algarve: {total_ada} registos")
    print(f"ULS Algarve: {total_uls} registos")
    print(f"TOTAL: {len(lista_final)} registos")
    print(f"Ficheiro atualizado: {FICHEIRO_SAIDA}")


if __name__ == "__main__":
    main()
