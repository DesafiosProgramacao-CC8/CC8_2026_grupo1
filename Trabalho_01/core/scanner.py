import os
from typing import Iterator

from core.config import EXTENSOES_IMAGEM, EXTENSOES_DOCUMENTO


def _ao_encontrar_erro(erro: OSError) -> None:
    print(f"[scanner] Aviso: não foi possível acessar '{erro.filename}': {erro}")


def varrer_pasta(caminho_raiz: str) -> Iterator[str]:
    #percorre recursivamente caminho_raiz, gerando o caminho completo
    for diretorio_atual, _subpastas, arquivos in os.walk(
        caminho_raiz, onerror=_ao_encontrar_erro
    ):
        for nome_arquivo in arquivos:
            caminho_completo = os.path.join(diretorio_atual, nome_arquivo)
            try:
                if not os.path.isfile(caminho_completo):
                    continue
                with open(caminho_completo, "rb"):
                    pass
                yield caminho_completo
            except OSError as e:
                print(f"[scanner] Aviso: sem permissão de leitura / erro ao acessar '{caminho_completo}': {e}")
                continue


def classificar_arquivo(caminho: str) -> str | None:
    _raiz, extensao = os.path.splitext(caminho)
    extensao = extensao.lower()
    if extensao in EXTENSOES_IMAGEM:
        return "imagem"
    if extensao in EXTENSOES_DOCUMENTO:
        return "documento"
    return None