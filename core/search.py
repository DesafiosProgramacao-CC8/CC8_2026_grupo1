import re
from core.indexer import tokenizar

BONUS_PALAVRA_EXATA = 1
PADRAO_CAMPO = re.compile(r"^(\w+):(\S+)$")

def extrair_termos_de_busca(termo):
    termos = []
    for pedaco in termo.strip().replace("+", " ").split():
        casou = PADRAO_CAMPO.match(pedaco)
        if casou:
            campo, valor = casou.groups()
            termos.append(f"{campo.lower()}:{valor.lower()}")
        else:
            termos.extend(tokenizar(pedaco))
    return termos

def _pontuar_termo(arvores, palavra):
    pontos = {}

    for arvore in arvores:
        for caminho, frequencia in arvore.buscar_prefixo(palavra).items():
            pontos[caminho] = pontos.get(caminho, 0) + frequencia

        for caminho, frequencia in arvore.buscar(palavra).items():
            pontos[caminho] = pontos.get(caminho, 0) + frequencia * BONUS_PALAVRA_EXATA

    return pontos

def buscar(indexador, termo, tipo):
    if tipo == "todos":
        arvores = [indexador.indices.arvore_imagens, indexador.indices.arvore_documentos]
    else:
        arvores = [indexador.indices.arvore_para_tipo(tipo)]

    palavras = extrair_termos_de_busca(termo)

    if not palavras:
        return []

    pontuacao_por_termo = [_pontuar_termo(arvores, palavra) for palavra in palavras]

    caminhos_validos = set(pontuacao_por_termo[0])
    for pontos_termo in pontuacao_por_termo[1:]:
        caminhos_validos &= set(pontos_termo)

    pontuacao = {
        caminho: sum(pontos_termo.get(caminho, 0) for pontos_termo in pontuacao_por_termo)
        for caminho in caminhos_validos
    }

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