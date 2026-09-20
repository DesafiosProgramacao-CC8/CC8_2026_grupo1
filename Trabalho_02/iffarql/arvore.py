from __future__ import annotations
from typing import Iterator

from iffarql.erros import ErroIffarql

Registro = dict[str, object]

LARGURA_ID = 10  # ids de 0 a 9_999_999_999


def _cabe(chave: int) -> bool:
    return 0 <= chave < 10**LARGURA_ID


def _digitos(chave: int) -> str:
    return str(chave).zfill(LARGURA_ID)


class No:
    def __init__(self) -> None:
        self.filhos: dict[str, No] = {}  # digito -> no
        self.registro: Registro | None = None  # so o no do ultimo digito guarda


class Arvore:
    def __init__(self) -> None:
        self.raiz = No()

    def inserir(self, chave: int, registro: Registro) -> None:
        #Erro se a chave nao couber em LARGURA_ID digitos ou ja existir
        if not _cabe(chave):
            raise ErroIffarql(f"id {chave} fora do limite de {LARGURA_ID} digitos")
        no = self.raiz
        for digito in _digitos(chave):
            if digito not in no.filhos:
                no.filhos[digito] = No()
            no = no.filhos[digito]
        if no.registro is not None:
            raise ErroIffarql(f"id {chave} ja existe")
        no.registro = registro

    def buscar(self, chave: int) -> Registro | None:
        if not _cabe(chave):
            return None
        no = self.raiz
        for digito in _digitos(chave):
            no = no.filhos.get(digito)
            if no is None:
                return None
        return no.registro

    def remover(self, chave: int) -> bool:
        if not _cabe(chave):
            return False
        caminho: list[tuple[No, str]] = []  # (pai, digito que leva ao filho)
        no = self.raiz
        for digito in _digitos(chave):
            filho = no.filhos.get(digito)
            if filho is None:
                return False
            caminho.append((no, digito))
            no = filho
        if no.registro is None:
            return False
        no.registro = None
        for pai, digito in reversed(caminho):
            filho = pai.filhos[digito]
            if filho.registro is not None or filho.filhos:
                break
            del pai.filhos[digito]
        return True

    def percorrer(self) -> Iterator[Registro]:
        """DFS iterativa em ordem crescente de id.
        Base de toda consulta que nao usa id. E um gerador: quem for remover
        durante a consulta deve antes coletar os ids (ex.: list(percorrer())).
        """
        pilha = [self.raiz]
        while pilha:
            no = pilha.pop()
            if no.registro is not None:
                yield no.registro
            # empilha do maior para o menor: o menor digito sai primeiro
            for digito in sorted(no.filhos, reverse=True):
                pilha.append(no.filhos[digito])

    def vazia(self) -> bool:
        return not self.raiz.filhos

    @classmethod
    def de_lista(cls, registros: list[Registro]) -> "Arvore":
    
        arvore = cls()
        for registro in registros:
            arvore.inserir(registro["id"], registro)
        return arvore
