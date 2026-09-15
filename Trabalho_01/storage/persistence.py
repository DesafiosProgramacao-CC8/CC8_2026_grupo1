import os
import pickle
from core.config import CAMINHO_INDICE_SALVO


def salvar_indice(indexador, caminho: str = CAMINHO_INDICE_SALVO) -> None:
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    try:
        with open(caminho, "wb") as f:
            pickle.dump(indexador, f)
    except Exception as e:
        print(f"[persistence] Erro ao salvar índice: {e}")


def carregar_indice(caminho: str = CAMINHO_INDICE_SALVO):
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[persistence] Erro ao carregar índice salvo (será recriado do zero): {e}")
        return None
