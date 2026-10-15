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
