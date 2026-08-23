from core.indexer import tokenizar

BONUS_PALAVRA_EXATA = 1

def buscar(indexador, termo, tipo):
    if tipo == "todos":
        arvores = [indexador.indices.arvore_imagens, indexador.indices.arvore_documentos]
    else:
        arvores = [indexador.indices.arvore_para_tipo(tipo)]

    palavras = tokenizar(termo)

    pontuacao = {}

    for arvore in arvores:
        for palavra in palavras:
            #busca por prefixo
            for caminho, frequencia in arvore.buscar_prefixo(palavra).items():
                pontuacao[caminho] = pontuacao.get(caminho, 0) + frequencia

            #busca exata
            for caminho, frequencia in arvore.buscar(palavra).items():
                pontuacao[caminho] = pontuacao.get(caminho, 0) + frequencia * BONUS_PALAVRA_EXATA

    resultados = []

    for caminho, relevancia in pontuacao.items():
        info = indexador.registro_arquivos[caminho]

        resultados.append({
            "nome": info["nome"], 
            "caminho": info["caminho"],
            "tipo": info["tipo"],
            "tamanho_bytes": info["tamanho_bytes"],
            "metadados": info["metadados"],
            "relevancia": relevancia
        })

    resultados.sort(key=lambda x: x["relevancia"], reverse=True)

    return resultados