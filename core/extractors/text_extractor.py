import os
from core.config import LIMITE_LEITURA_TEXTO


def extrair_texto(caminho: str, limite_bytes: int = LIMITE_LEITURA_TEXTO) -> str:
    try:
        tamanho = os.path.getsize(caminho)
        if tamanho > limite_bytes:
            print(f"[text_extractor] Arquivo grande, lendo parcialmente: {caminho}")

        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(limite_bytes)

    except (OSError, PermissionError) as e:
        print(f"[text_extractor] Não foi possível ler '{caminho}': {e}")
        return ""
