import os
from typing import Any, Dict
from PIL import Image


def extrair_metadados(caminho: str) -> Dict[str, Any]:
    stat = os.stat(caminho)
    metadados: Dict[str, Any] = {
        "tamanho_bytes": stat.st_size,
        "modificado_em": stat.st_mtime,
        "largura": None,
        "altura": None,
        "formato": None,
        "modo_cor": None,
    }

    try:
        with Image.open(caminho) as img:
            metadados["largura"], metadados["altura"] = img.size
            metadados["formato"] = img.format
            metadados["modo_cor"] = img.mode
    except Exception as e:
        print(f"[image_extractor] Não foi possível ler metadados de '{caminho}': {e}")

    return metadados
