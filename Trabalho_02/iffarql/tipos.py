from __future__ import annotations

import operator as _op
import re

from iffarql.erros import ErroIffarql

_ARITMETICOS = {
    "+": _op.add,
    "-": _op.sub,
    "*": _op.mul,
    "/": _op.truediv,
}

_COMPARADORES = {
    "<": _op.lt,
    "<=": _op.le,
    ">": _op.gt,
    ">=": _op.ge,
    "==": _op.eq,
    "<>": _op.ne,
}

TODOS_COMPARADORES = frozenset(_COMPARADORES)


def _tirar_aspas(bruto: str) -> str:
    texto = bruto.strip()
    if len(texto) >= 2 and texto[0] == '"' and texto[-1] == '"':
        return texto[1:-1]
    return texto


def _exigir_aspas(bruto: str, nome_tipo: str) -> str:
    #conteudo entre aspas, erro se o valor nao vier entre aspas
    texto = bruto.strip()
    if len(texto) < 2 or texto[0] != '"' or texto[-1] != '"':
        raise ErroIffarql(f"valor '{bruto}' precisa estar entre aspas para o tipo {nome_tipo}")
    return texto[1:-1]


class Tipo:
    nome = ""
    operadores_aritmeticos: frozenset[str] = frozenset()
    operadores_comparacao: frozenset[str] = TODOS_COMPARADORES

    def converter(self, bruto: str):
        raise NotImplementedError

    def formatar(self, valor) -> str:
        return str(valor)
    
    def tipo_operando(self, op: str) -> "Tipo":
        return self

    def operar(self, a, op: str, b):
        if op not in self.operadores_aritmeticos:
            raise ErroIffarql(
                f"operador '{op}' nao e permitido para o tipo {self.nome}"
            )
        return self._operar(a, op, b)

    def comparar(self, a, op: str, b) -> bool:
        if op not in self.operadores_comparacao:
            raise ErroIffarql(
                f"operador '{op}' nao e permitido para o tipo {self.nome}"
            )
        return self._comparar(a, op, b)

    def _operar(self, a, op: str, b):
        return _ARITMETICOS[op](a, b)

    def _comparar(self, a, op: str, b) -> bool:
        return _COMPARADORES[op](a, b)


class Inteiro(Tipo):
    nome = "INTEIRO"
    operadores_aritmeticos = frozenset({"+", "-", "*", "/"})

    _PADRAO = re.compile(r"[+-]?\d+")

    def converter(self, bruto: str) -> int:
        texto = bruto.strip()
        if not self._PADRAO.fullmatch(texto):
            raise ErroIffarql(f"valor '{bruto}' nao e um INTEIRO valido")
        return int(texto)

    def _operar(self, a: int, op: str, b: int):
        if op == "/":
            if b == 0:
                raise ErroIffarql("divisao por zero")
            return a // b  
        return _ARITMETICOS[op](a, b)


class Decimal(Tipo):
    nome = "DECIMAL"
    operadores_aritmeticos = frozenset({"+", "-", "*", "/"})

    _PADRAO = re.compile(r"[+-]?\d+(\.\d+)?")

    def converter(self, bruto: str) -> float:
        texto = bruto.strip()
        if not self._PADRAO.fullmatch(texto):
            raise ErroIffarql(f"valor '{bruto}' nao e um DECIMAL valido")
        return float(texto)

    def _operar(self, a: float, op: str, b: float):
        if op == "/" and b == 0:
            raise ErroIffarql("divisao por zero")
        return _ARITMETICOS[op](a, b)

    def formatar(self, valor: float) -> str:
        return f"{valor:.2f}"


class Booleano(Tipo):
    nome = "BOOLEANO"
    operadores_aritmeticos = frozenset()  # nenhuma operação aritmética
    operadores_comparacao = frozenset({"==", "<>"})

    _VALORES = {"true": True, "false": False}

    def converter(self, bruto: str) -> bool:
        texto = _tirar_aspas(bruto).strip().lower()
        if texto not in self._VALORES:
            raise ErroIffarql(f"valor '{bruto}' nao e um BOOLEANO valido")
        return self._VALORES[texto]

    def formatar(self, valor: bool) -> str:
        return "true" if valor else "false"


_TRADUCAO_ACENTOS = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçñýÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑÝ",
    "aaaaaeeeeiiiiooooouuuucnyAAAAAEEEEIIIIOOOOOUUUUCNY",
)


class Texto(Tipo):
    nome = "TEXTO"
    operadores_aritmeticos = frozenset({"+"})  # concatenação

    def converter(self, bruto: str) -> str:
        texto = _exigir_aspas(bruto, self.nome)
        return texto.translate(_TRADUCAO_ACENTOS)

    def _operar(self, a: str, op: str, b: str) -> str:
        return a + b

_DIAS_MES = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
             7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _serial(dia: int, mes: int, ano: int) -> int:
    dias_antes = sum(_DIAS_MES[m] for m in range(1, mes))
    return ano * 365 + dias_antes + (dia - 1)


def _de_serial(serial: int) -> tuple[int, int, int]:
    ano, resto = divmod(serial, 365)
    mes = 1
    while resto >= _DIAS_MES[mes]:
        resto -= _DIAS_MES[mes]
        mes += 1
    return resto + 1, mes, ano


_SERIAL_MIN = _serial(1, 1, 1)  # 01/01/0001
_SERIAL_MAX = _serial(31, 12, 9999)  # 31/12/9999


class Data(Tipo):

    nome = "DATA"
    operadores_aritmeticos = frozenset({"+", "-"})

    _PADRAO = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

    def converter(self, bruto: str) -> tuple[int, int, int]:
        texto = _exigir_aspas(bruto, self.nome)
        m = self._PADRAO.fullmatch(texto)
        if not m:
            raise ErroIffarql(f"valor '{bruto}' nao e uma DATA valida (dd/mm/aaaa)")
        dia, mes, ano = int(m[1]), int(m[2]), int(m[3])
        if not (1 <= mes <= 12):
            raise ErroIffarql(f"mes invalido em '{bruto}'")
        if not (1 <= ano <= 9999):
            raise ErroIffarql(f"ano invalido em '{bruto}'")
        if not (1 <= dia <= _DIAS_MES[mes]):
            raise ErroIffarql(f"dia invalido em '{bruto}' para o mes {mes:02d}")
        return (dia, mes, ano)

    def formatar(self, valor: tuple[int, int, int]) -> str:
        dia, mes, ano = valor
        return f"{dia:02d}/{mes:02d}/{ano:04d}"

    def _operar(self, a: tuple[int, int, int], op: str, b: int):
        serial = _serial(*a)
        serial = serial + b if op == "+" else serial - b
        if not (_SERIAL_MIN <= serial <= _SERIAL_MAX):
            raise ErroIffarql("resultado fora do intervalo de datas validas (01/01/0001 a 31/12/9999)")
        return _de_serial(serial)

    def _comparar(self, a: tuple[int, int, int], op: str, b: tuple[int, int, int]) -> bool:
        return _COMPARADORES[op](_serial(*a), _serial(*b))
    
    def tipo_operando(self, op: str) -> "Tipo":
        return _TIPOS["INTEIRO"]


_TIPOS: dict[str, Tipo] = {
    "INTEIRO": Inteiro(),
    "DECIMAL": Decimal(),
    "BOOLEANO": Booleano(),
    "TEXTO": Texto(),
    "DATA": Data(),
}


def obter_tipo(nome: str) -> Tipo:
    try:
        return _TIPOS[nome.strip().upper()]
    except KeyError:
        raise ErroIffarql(f"tipo '{nome}' nao existe")