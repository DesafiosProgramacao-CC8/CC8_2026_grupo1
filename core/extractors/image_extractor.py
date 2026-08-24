import os
from datetime import datetime
from typing import Any, Dict
from PIL import Image, ImageChops

MODOS_PRETO_E_BRANCO = {"1", "L", "LA", "I", "F"}
TOLERANCIA_CINZA = 16

def _e_tons_de_cinza(img) -> bool:
    if img.mode in MODOS_PRETO_E_BRANCO:
        return True
    try:
        img.draft("RGB", (128, 128))
    except Exception:
        pass

    amostra = img.convert("RGB")
    amostra.thumbnail((128, 128))
    r, g, b = amostra.split()

    return max(
        ImageChops.difference(r, g).getextrema()[1],
        ImageChops.difference(g, b).getextrema()[1],
        ImageChops.difference(r, b).getextrema()[1],
    ) <= TOLERANCIA_CINZA

def _tons_de_cinza(metadados: Dict[str, Any]) -> bool:
    valor = metadados.get("tons_de_cinza")
    if valor is None:
        return metadados.get("modo_cor") in MODOS_PRETO_E_BRANCO
    return valor


def extrair_metadados(caminho: str) -> Dict[str, Any]:
    stat = os.stat(caminho)
    metadados: Dict[str, Any] = {
        "tamanho_bytes": stat.st_size,
        "modificado_em": stat.st_mtime,
        "largura": None,
        "altura": None,
        "formato": None,
        "modo_cor": None,
        "tons_de_cinza": None,
    }

    try:
        with Image.open(caminho) as img:
            metadados["largura"], metadados["altura"] = img.size
            metadados["formato"] = img.format
            metadados["modo_cor"] = img.mode
            metadados["tons_de_cinza"] = _e_tons_de_cinza(img)
    except Exception as e:
        print(f"[image_extractor] Não foi possível ler metadados de '{caminho}': {e}")

    return metadados


def gerar_termos_busca(metadados: Dict[str, Any]):
    termos = []

    formato = metadados.get("formato")
    if formato:
        termos.append(formato.lower())

    largura = metadados.get("largura")
    altura = metadados.get("altura")

    if largura and altura:
        termos.append(f"{largura}x{altura}")
        termos.append(str(largura))
        termos.append(str(altura))

        if largura > altura:
            termos.extend(["paisagem", "horizontal"])
        elif altura > largura:
            termos.extend(["retrato", "vertical"])
        else:
            termos.append("quadrada")

        maior_lado = max(largura, altura)
        if maior_lado >= 1920:
            termos.append("grande")
        elif maior_lado <= 400:
            termos.append("pequena")
        else:
            termos.append("media")

    modo_cor = metadados.get("modo_cor")
    if modo_cor:
        termos.append(modo_cor.lower())

        #imagem em tons de cinza / preto e branco
        if _tons_de_cinza(metadados):
            termos.extend(["preta", "branca", "pb", "bw", "cinza", "grayscale"])
        else:
            termos.extend(["colorida", "cor", "color"])

    tamanho_bytes = metadados.get("tamanho_bytes")
    if tamanho_bytes is not None:
        #peso do arquivo (não confundir com o tamanho em pixels)
        if tamanho_bytes < 100_000:  # < ~100 KB
            termos.append("leve")
        elif tamanho_bytes > 2_000_000:  # > ~2 MB
            termos.append("pesada")
        else:
            termos.append("moderada")

    modificado_em = metadados.get("modificado_em")
    if modificado_em:
        ano = datetime.fromtimestamp(modificado_em).year
        termos.append(str(ano))

    return termos

def _classificar_resolucao(largura: int, altura: int) -> str:
    maior_lado = max(largura, altura)
    if maior_lado >= 1920:
        return "grande"
    if maior_lado <= 400:
        return "pequena"
    return "media"


def _classificar_peso(tamanho_bytes: int) -> str:
    if tamanho_bytes < 100_000:
        return "leve"
    if tamanho_bytes > 2_000_000:
        return "pesada"
    return "moderada"


def gerar_termos_por_campo(metadados: Dict[str, Any]):
    campos = []

    formato = metadados.get("formato")
    if formato:
        formato = formato.lower()
        campos.append(("tipo", formato))
        if formato == "jpeg":
            campos.append(("tipo", "jpg"))

    largura = metadados.get("largura")
    altura = metadados.get("altura")

    if largura and altura:
        if largura > altura:
            campos.append(("orientacao", "horizontal"))
        elif altura > largura:
            campos.append(("orientacao", "vertical"))
        else:
            campos.append(("orientacao", "quadrada"))

        campos.append(("tamanho", _classificar_resolucao(largura, altura)))

    modo_cor = metadados.get("modo_cor")
    if modo_cor:
        campos.append(("cor", "pb" if _tons_de_cinza(metadados) else "colorida"))

    tamanho_bytes = metadados.get("tamanho_bytes")
    if tamanho_bytes is not None:
        campos.append(("peso", _classificar_peso(tamanho_bytes)))

    modificado_em = metadados.get("modificado_em")
    if modificado_em:
        campos.append(("ano", str(datetime.fromtimestamp(modificado_em).year)))

    return campos