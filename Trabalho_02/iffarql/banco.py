"""Camada 3 - Nucleo do BD: tabelas, integridade referencial, ACID e arquivo."""

from __future__ import annotations
import json
import os
import tempfile
from contextlib import contextmanager
from typing import Iterator

from iffarql.erros import ErroIffarql
from iffarql.expressoes import Atribuicao, Coluna, Condicao
from iffarql.tabela import Registro, Tabela

# usado pelo auto-salvar enquanto nenhum SALVARBD/CARREGARBD definiu o arquivo
ARQUIVO_TEMPORARIO = os.path.join(tempfile.gettempdir(), "iffarql_temp.json")


class Banco:
    def __init__(self) -> None:
        self.tabelas: dict[str, Tabela] = {}
        self.arquivo: str | None = None  # definido por SALVARBD/CARREGARBD
        self._em_transacao = False

    def criar_tabela(self, nome: str, colunas: list[Coluna]) -> None:
        """erro se ja existir, se a FK apontar tabela inexistente ou se
        o usuario tentar declarar uma coluna chamada id."""
        if nome in self.tabelas:
            raise ErroIffarql(f"tabela '{nome}' ja existe")
        for coluna in colunas:
            if coluna.chave_estrangeira is None:
                continue
            if coluna.chave_estrangeira not in self.tabelas:
                raise ErroIffarql(
                    f"coluna '{coluna.nome}' referencia a tabela inexistente "
                    f"'{coluna.chave_estrangeira}'"
                )
            if coluna.tipo.nome != "INTEIRO":
                raise ErroIffarql(f"chave estrangeira '{coluna.nome}' precisa ser INTEIRO")
        self.tabelas[nome] = Tabela(nome, colunas)  # valida id e nomes repetidos

    def apagar_tabela(self, nome: str) -> None:
        #erro se tiver registros ou se outra tabela apontar para ela
        tabela = self.obter(nome)
        if not tabela.vazia():
            raise ErroIffarql(f"tabela '{nome}' ainda tem registros")
        for outra in self.tabelas.values():
            if any(c.chave_estrangeira == nome for c in outra.chaves_estrangeiras()):
                raise ErroIffarql(f"tabela '{outra.nome}' referencia '{nome}'")
        del self.tabelas[nome]

    def obter(self, nome: str) -> Tabela:
        #erro se a tabela nao existir
        try:
            return self.tabelas[nome]
        except KeyError:
            raise ErroIffarql(f"tabela '{nome}' nao existe")

    def selecionar(self, nome: str, condicao: Condicao | None) -> list[Registro]:
        return self.obter(nome).selecionar(condicao)

    def inserir(self, nome: str, brutos: list[str]) -> int:
        tabela = self.obter(nome)
        registro = tabela.converter_valores(brutos)
        self.validar_referencias(tabela, registro)
        return tabela.inserir(registro)

    def atualizar(self, nome: str, atribuicoes: list[Atribuicao], condicao: Condicao | None) -> int:
        """Devolve quantos registros mudaram. So grava se todos forem validos.
        O id nao muda, entao nenhuma FK de outra tabela pode quebrar: basta
        validar as FKs dos proprios registros alterados.
        """
        tabela = self.obter(nome)
        novos = tabela.atualizar(atribuicoes, condicao)
        for novo in novos:
            self.validar_referencias(tabela, novo)
        tabela.gravar(novos)
        return len(novos)

    def apagar_dados(self, nome: str, condicao: Condicao | None) -> int:
        tabela = self.obter(nome)
        ids = [r["id"] for r in tabela.selecionar(condicao)]
        bloqueios = self.referenciam(nome, ids)
        if bloqueios:
            exemplos = ", ".join(f"{t} (id {i})" for t, i in bloqueios[:3])
            raise ErroIffarql(f"registros de '{nome}' sao referenciados por: {exemplos}")
        return len(tabela.apagar(condicao))

    def validar_referencias(self, tabela: Tabela, registro: dict) -> None:
        #Toda FK do registro precisa existir na tabela referenciada
        for coluna in tabela.chaves_estrangeiras():
            alvo = self.obter(coluna.chave_estrangeira)
            valor = registro[coluna.nome]
            if alvo.arvore.buscar(valor) is None:
                raise ErroIffarql(
                    f"'{coluna.nome}' = {valor}: nao existe registro com esse id "
                    f"em '{alvo.nome}'"
                )

    def referenciam(self, nome_tabela: str, ids: list[int]) -> list[tuple[str, int]]:
        if not ids:
            return []
        procurados = set(ids)
        achados = []
        for outra in self.tabelas.values():
            for coluna in outra.chaves_estrangeiras():
                if coluna.chave_estrangeira != nome_tabela:
                    continue
                for registro in outra.arvore.percorrer():
                    if registro[coluna.nome] in procurados:
                        achados.append((outra.nome, registro["id"]))
        return achados

    @contextmanager
    def transacao(self) -> Iterator[None]:
        """Snapshot antes, rollback no erro, auto-salvar no sucesso.
        Aninhada (ex.: comandos dentro de um CARREGARIFFARQL) nao faz nada:
        so a transacao mais externa restaura ou salva.
        ponytail: snapshot por para_dict/de_dict das tabelas; virar journal/WAL
        so se o volume de dados tornar a copia cara.
        """
        if self._em_transacao:
            yield
            return
        instantaneo = self._capturar()
        self._em_transacao = True
        try:
            yield
            self.salvar()  # durabilidade; se falhar, desfaz para nao divergir do disco
        except BaseException:
            self._restaurar(instantaneo)
            raise
        finally:
            self._em_transacao = False

    def _capturar(self) -> tuple[str | None, dict[str, dict]]:
        return self.arquivo, {nome: t.para_dict() for nome, t in self.tabelas.items()}

    def _restaurar(self, instantaneo: tuple[str | None, dict[str, dict]]) -> None:
        self.arquivo, tabelas = instantaneo
        self.tabelas = {nome: Tabela.de_dict(d) for nome, d in tabelas.items()}

    def salvar(self, nome_arquivo: str | None = None) -> None:
        """JSON com esquema, registros e proximo_id de cada tabela.
        Sem nome, usa o arquivo em uso ou o temporario. Escreve num .tmp e
        troca de uma vez, para uma falha nunca deixar o arquivo pela metade.
        """
        destino = nome_arquivo or self.arquivo or ARQUIVO_TEMPORARIO
        dados = {"tabelas": [t.para_dict() for t in self.tabelas.values()]}
        parcial = destino + ".tmp"
        try:
            with open(parcial, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            os.replace(parcial, destino)
        except OSError as erro:
            if os.path.exists(parcial):
                os.unlink(parcial)
            raise ErroIffarql(f"nao foi possivel salvar em '{destino}': {erro}")
        if nome_arquivo:
            self.arquivo = nome_arquivo

    def carregar(self, nome_arquivo: str) -> None:
        #Erro se ja houver tabela criada. Remonta as arvores balanceadas
        if self.tabelas:
            raise ErroIffarql("CARREGARBD so pode ser usado sem tabelas criadas")
        carregou = False
        try:
            with open(nome_arquivo, encoding="utf-8") as f:
                dados = json.load(f)
            tabelas: dict[str, Tabela] = {}
            for dados_tabela in dados["tabelas"]:
                tabela = Tabela.de_dict(dados_tabela)
                if tabela.nome in tabelas:
                    raise ErroIffarql(f"tabela '{tabela.nome}' repetida no arquivo")
                tabelas[tabela.nome] = tabela
            self.tabelas = tabelas
            self._validar_integridade()
            self.arquivo = nome_arquivo
            carregou = True
        except FileNotFoundError:
            raise ErroIffarql(f"arquivo '{nome_arquivo}' nao encontrado")
        except (OSError, ValueError, KeyError, TypeError) as erro:
            raise ErroIffarql(f"arquivo '{nome_arquivo}' invalido: {erro!r}")
        finally:
            if not carregou:
                self.tabelas = {}

    def _validar_integridade(self) -> None:
        for tabela in self.tabelas.values():
            for coluna in tabela.chaves_estrangeiras():
                if coluna.chave_estrangeira not in self.tabelas:
                    raise ErroIffarql(
                        f"'{tabela.nome}.{coluna.nome}' referencia a tabela inexistente "
                        f"'{coluna.chave_estrangeira}'"
                    )
                if coluna.tipo.nome != "INTEIRO":
                    raise ErroIffarql(f"chave estrangeira '{coluna.nome}' precisa ser INTEIRO")
            for registro in tabela.arvore.percorrer():
                self.validar_referencias(tabela, registro)
