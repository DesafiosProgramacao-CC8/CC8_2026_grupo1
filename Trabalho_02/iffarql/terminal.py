# Gerado com auxilio de IA
# Objetivo: separar a aparencia da logica

import os
import sys

_CORES = {
    "titulo": "\033[96m",
    "destaque": "\033[93m",
    "borda": "\033[90m",
    "cabecalho": "\033[1m",
    "erro": "\033[91m",
    "ok": "\033[92m",
    "fraco": "\033[90m",
}

_FIM = "\033[0m"

def _terminal_rico() -> bool:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return False
    return True

RICO = _terminal_rico()


_MOLDURA = "┌┬┐├┼┤└┴┘│─" if RICO else "+++++++++|-"


def cor(texto: str, nome: str) -> str:
    return f"{_CORES[nome]}{texto}{_FIM}" if RICO else texto


def _linha(larguras: list[int], esquerda: str, meio: str, direita: str) -> str:
    traco = _MOLDURA[10]
    return cor(esquerda + meio.join(traco * (l + 2) for l in larguras) + direita, "borda")


def tabelar(colunas, registros: list[dict]) -> str:
    cabecalho = [c.nome for c in colunas]
    linhas = [[c.tipo.formatar(r[c.nome]) for c in colunas] for r in registros]
    larguras = [
        max(len(cabecalho[i]), max((len(l[i]) for l in linhas), default=0))
        for i in range(len(cabecalho))
    ]
    barra = cor(_MOLDURA[9], "borda")

    def montar(campos: list[str], estilo: str | None = None) -> str:
        celulas = [
            cor(v.ljust(larguras[i]), estilo) if estilo else v.ljust(larguras[i])
            for i, v in enumerate(campos)
        ]
        return f"{barra} " + f" {barra} ".join(celulas) + f" {barra}"

    saida = [
        _linha(larguras, _MOLDURA[0], _MOLDURA[1], _MOLDURA[2]),
        montar(cabecalho, "cabecalho"),
        _linha(larguras, _MOLDURA[3], _MOLDURA[4], _MOLDURA[5]),
        *(montar(l) for l in linhas),
        _linha(larguras, _MOLDURA[6], _MOLDURA[7], _MOLDURA[8]),
        cor(f"{len(registros)} registro(s)", "fraco"),
    ]
    return "\n".join(saida)


_LOGO = r"""
 ___  ________ ________ ________  ________  ________  ___          
|\  \|\  _____\\  _____\\   __  \|\   __  \|\   __  \|\  \         
\ \  \ \  \__/\ \  \__/\ \  \|\  \ \  \|\  \ \  \|\  \ \  \        
 \ \  \ \   __\\ \   __\\ \   __  \ \   _  _\ \  \\\  \ \  \       
  \ \  \ \  \_| \ \  \_| \ \  \ \  \ \  \\  \\ \  \\\  \ \  \____  
   \ \__\ \__\   \ \__\   \ \__\ \__\ \__\\ _\\ \_____  \ \_______\
    \|__|\|__|    \|__|    \|__|\|__|\|__|\|__|\|___| \__\|_______|
                                                     \|__|         
"""

_LOGO_CORTE = (43, 43, 43, 44, 45, 46, 47, 0)


def _logo_colorido() -> str:
    linhas = _LOGO.strip("\n").split("\n")
    return "\n".join(
        cor(l[:c], "titulo") + cor(l[c:], "destaque")
        for l, c in zip(linhas, _LOGO_CORTE)
    )


def abertura() -> str:
    if not RICO:
        return "IFFARQL - AJUDA lista os comandos, SAIR encerra.\n"
    return "\n".join([
        _logo_colorido(),
        cor("  Sistema Gerenciador de Banco de Dados - IFFar FW", "fraco"),
        "",
        f"  {cor('AJUDA', 'ok')} lista os comandos    "
        f"{cor('SAIR', 'ok')} encerra o terminal",
        "",
    ])


def ajuda(comandos: dict) -> str:
    largura = max(len(p) for p in comandos)
    linhas = [cor("Comandos da linguagem IFFARQL:", "cabecalho")]
    for palavra in sorted(comandos):
        sintaxe = comandos[palavra].sintaxe
        linhas.append(f"  {cor(palavra.ljust(largura), 'titulo')}  {sintaxe}")
    linhas += [
        "",
        cor("Comandos do terminal:", "cabecalho"),
        f"  {cor('AJUDA'.ljust(largura), 'titulo')}  mostra esta tela",
        f"  {cor('SAIR'.ljust(largura), 'titulo')}  encerra o terminal",
        "",
        cor("Tipos: INTEIRO DECIMAL BOOLEANO TEXTO DATA", "fraco"),
        cor('TEXTO e DATA vao entre aspas; DATA no formato "dd/mm/aaaa".', "fraco"),
    ]
    return "\n".join(linhas)
