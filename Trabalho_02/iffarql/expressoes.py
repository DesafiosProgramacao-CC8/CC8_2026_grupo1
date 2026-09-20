from __future__ import annotations

from dataclasses import dataclass

from iffarql.erros import ErroIffarql
from iffarql.tipos import TODOS_COMPARADORES, Tipo


@dataclass(frozen=True)
class Coluna:

    nome: str
    tipo: Tipo
    chave_estrangeira: str | None = None  # nome da tabela referenciada, se houver


Esquema = dict[str, Coluna] 


def criar_esquema(colunas: list[Coluna]) -> Esquema:
    nomes = [c.nome for c in colunas]
    if "id" in nomes:
        raise ErroIffarql("o usuario nao pode declarar uma coluna chamada 'id'")
    repetidas = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidas:
        raise ErroIffarql(f"coluna(s) declarada(s) mais de uma vez: {', '.join(repetidas)}")
    return {c.nome: c for c in colunas}


def _coluna(esquema: Esquema, nome: str) -> Coluna:
    try:
        return esquema[nome]
    except KeyError:
        raise ErroIffarql(f"coluna '{nome}' nao existe nesta tabela")


def montar_registro(esquema: Esquema, valores_brutos: list[str]) -> dict:
    colunas = list(esquema.values())
    if len(valores_brutos) != len(colunas):
        raise ErroIffarql(
            f"esperado {len(colunas)} valor(es), recebido {len(valores_brutos)}"
        )
    registro = {}
    for col, bruto in zip(colunas, valores_brutos):
        if bruto is None or bruto.strip() == "":
            raise ErroIffarql(f"valor nulo nao e permitido para a coluna '{col.nome}'")
        registro[col.nome] = col.tipo.converter(bruto)
    return registro


def avaliar_condicao(
    registro: dict, esquema: Esquema, coluna: str, operador: str, valor_bruto: str
) -> bool:
    if operador not in TODOS_COMPARADORES:
        raise ErroIffarql(f"'{operador}' nao e um comparador valido")
    col = _coluna(esquema, coluna)
    valor_convertido = col.tipo.converter(valor_bruto)
    return col.tipo.comparar(registro[coluna], operador, valor_convertido)


def resolver_atribuicao(
    registro: dict, esquema: Esquema, coluna: str, tokens_valor: list[str]
):

    if coluna == "id":
        raise ErroIffarql("o campo id nao pode ser modificado")
    col = _coluna(esquema, coluna)

    if len(tokens_valor) == 1:
        return col.tipo.converter(tokens_valor[0])

    if len(tokens_valor) == 3:
        nome_ref, op, operando_bruto = tokens_valor
        if nome_ref != coluna:
            raise ErroIffarql(
                f"'{nome_ref}' precisa ser a propria coluna '{coluna}' sendo atualizada"
            )
        tipo_operando = col.tipo.tipo_operando(op)
        operando = tipo_operando.converter(operando_bruto)
        return col.tipo.operar(registro[coluna], op, operando)

    raise ErroIffarql(f"expressao de atribuicao invalida: {tokens_valor!r}")


@dataclass(frozen=True)
class Condicao:

    coluna: str
    operador: str
    valor_bruto: str

    def avaliar(self, registro: dict, esquema: Esquema) -> bool:
        return avaliar_condicao(registro, esquema, self.coluna, self.operador, self.valor_bruto)


@dataclass(frozen=True)
class Atribuicao:

    coluna: str
    termos: tuple[str, ...] 

    def novo_valor(self, registro: dict, esquema: Esquema):
        return resolver_atribuicao(registro, esquema, self.coluna, list(self.termos))