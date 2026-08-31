import re
from typing import Dict

PALAVRAS_IGNORADAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "é", "em",
    "um", "uma", "uns", "umas", "que", "com", "para", "por", "no", "na",
    "nos", "nas", "se", "ao", "aos", "à", "às", "como", "mais", "mas",
    "the", "a", "an", "of", "and", "to", "in", "is", "it",
}

_PADRAO_PALAVRA = re.compile(r"[a-zA-ZÀ-ÿ0-9]+")


def contar_palavras(texto: str) -> Dict[str, int]:

    if not texto:
        return {}

    contagem: Dict[str, int] = {}
    for palavra in _PADRAO_PALAVRA.findall(texto.lower()):
        if len(palavra) <= 1 or palavra in PALAVRAS_IGNORADAS:
            continue
        contagem[palavra] = contagem.get(palavra, 0) + 1

    return contagem


def palavras_mais_comuns(frequencias: Dict[str, int], top_n: int = 10):
    return sorted(frequencias.items(), key=lambda par: par[1], reverse=True)[:top_n]
