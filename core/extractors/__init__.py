from typing import Any, Dict

from core.extractors.image_extractor import extrair_metadados as extrair_metadados_imagem
from core.extractors.text_extractor import extrair_texto
from core.relevance import contar_palavras

TAMANHO_TRECHO = 200


def extrair_dados_documento(caminho: str) -> Dict[str, Any]:
    texto = extrair_texto(caminho)

    return {
        "trecho": " ".join(texto.split())[:TAMANHO_TRECHO],
        "palavras": contar_palavras(texto),
    }

__all__ = ["extrair_metadados_imagem", "extrair_dados_documento"]