import sys

from iffarql import terminal
from iffarql.banco import Banco
from iffarql.comandos import COMANDOS, interpretar
from iffarql.erros import ErroIffarql

PROMPT = terminal.cor("iffarql> ", "titulo")


def executar_linha(bd: Banco, linha: str) -> str:
    comando = interpretar(linha)
    if not comando.altera_dados:
        return comando.executar(bd)
    with bd.transacao():
        return comando.executar(bd)


def repl() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    bd = Banco()
    print(terminal.abertura())
    while True:
        try:
            linha = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not linha:
            continue
        if linha == "SAIR":
            print(terminal.cor("ate mais.", "fraco"))
            return
        if linha == "AJUDA":
            print(terminal.ajuda(COMANDOS))
            continue
        try:
            print(executar_linha(bd, linha))
        except ErroIffarql as erro:
            print(terminal.cor(f"! {erro}", "erro"))


if __name__ == "__main__":
    repl()
