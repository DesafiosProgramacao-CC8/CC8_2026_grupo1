from __future__ import annotations

from iffarql.arvore import Arvore
from iffarql.erros import ErroIffarql
from iffarql.expressoes import Atribuicao, Coluna, Condicao, criar_esquema, montar_registro
from iffarql.tipos import Tipo, obter_tipo

Registro = dict[str, object]


def _valor_para_json(valor: object) -> object:
    return list(valor) if isinstance(valor, tuple) else valor  # DATA


def _valor_de_json(tipo: Tipo, valor: object) -> object:
    return tuple(valor) if tipo.nome == "DATA" else valor


class Tabela:
    def __init__(self, nome: str, colunas: list[Coluna]) -> None:
        if len({c.nome for c in colunas}) != len(colunas):
            raise ErroIffarql(f"tabela '{nome}' tem colunas com nome repetido")
        self.nome = nome
        self.esquema = criar_esquema(colunas)  # so as colunas do usuario
        self.esquema_completo = {"id": Coluna("id", obter_tipo("INTEIRO")), **self.esquema}
        self.arvore = Arvore()
        self.proximo_id = 1  # nunca decrementa

    @property
    def colunas(self) -> list[Coluna]:
        return list(self.esquema_completo.values())

    def coluna(self, nome: str) -> Coluna:
        #erro se a coluna nao existir
        try:
            return self.esquema_completo[nome]
        except KeyError:
            raise ErroIffarql(f"coluna '{nome}' nao existe na tabela '{self.nome}'")

    def converter_valores(self, brutos: list[str]) -> Registro:
        #valida quantidade e tipo dos valores do INSERIREM (sem o id)
        return montar_registro(self.esquema, brutos)

    def inserir(self, registro: Registro) -> int:
        id_novo = self.proximo_id
        self.arvore.inserir(id_novo, {"id": id_novo, **registro})
        self.proximo_id += 1
        return id_novo

    def _valor_da_condicao(self, condicao: Condicao) -> object:
        coluna = self.coluna(condicao.coluna)
        valor = coluna.tipo.converter(condicao.valor_bruto)
        coluna.tipo.comparar(valor, condicao.operador, valor)  # tipo recusa o operador?
        return valor

    def selecionar(self, condicao: Condicao | None) -> list[Registro]:
        """Registros que casam com o ONDE, em ordem de id.
        Devolve os proprios dicts da arvore: quem chama nao deve altera-los.
        """
        if condicao is None:
            return list(self.arvore.percorrer())
        valor = self._valor_da_condicao(condicao)
        if condicao.coluna == "id" and condicao.operador == "==":
            registro = self.arvore.buscar(valor)  # caminho rapido
            return [] if registro is None else [registro]
        return [
            r for r in self.arvore.percorrer()
            if condicao.avaliar(r, self.esquema_completo)
        ]

    def atualizar(self, atribuicoes: list[Atribuicao], condicao: Condicao | None) -> list[Registro]:
        """Devolve COPIAS ja alteradas, sem gravar (o Banco valida FK e chama gravar).
        Todas as atribuicoes leem o registro original. Se qualquer calculo
        falhar, nada foi alterado.
        """
        for atribuicao in atribuicoes:
            if atribuicao.coluna == "id":
                raise ErroIffarql("o campo id nao pode ser modificado")
            self.coluna(atribuicao.coluna)
        novos = []
        for original in self.selecionar(condicao):
            novo = dict(original)
            for atribuicao in atribuicoes:
                novo[atribuicao.coluna] = atribuicao.novo_valor(original, self.esquema_completo)
            novos.append(novo)
        return novos

    def gravar(self, registros: list[Registro]) -> None:
        for novo in registros:
            atual = self.arvore.buscar(novo["id"])
            if atual is None:
                raise ErroIffarql(f"registro {novo['id']} nao existe em '{self.nome}'")
            atual.update(novo)

    def apagar(self, condicao: Condicao | None) -> list[int]:
        ids = [r["id"] for r in self.selecionar(condicao)]  # coleta antes de remover
        for id_removido in ids:
            self.arvore.remover(id_removido)
        return ids

    def vazia(self) -> bool:
        return self.arvore.vazia()

    def chaves_estrangeiras(self) -> list[Coluna]:
        return [c for c in self.esquema.values() if c.chave_estrangeira]

    def para_dict(self) -> dict:
        return {
            "nome": self.nome,
            "proximo_id": self.proximo_id,
            "colunas": [
                {"nome": c.nome, "tipo": c.tipo.nome, "chave_estrangeira": c.chave_estrangeira}
                for c in self.esquema.values()
            ],
            "registros": [
                {k: _valor_para_json(v) for k, v in r.items()}  # copia: gravar altera no lugar
                for r in self.arvore.percorrer()
            ],
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Tabela":
        try:
            colunas = [
                Coluna(c["nome"], obter_tipo(c["tipo"]), c["chave_estrangeira"])
                for c in dados["colunas"]
            ]
            tabela = cls(dados["nome"], colunas)
            registros = [
                {nome: _valor_de_json(col.tipo, r[nome]) for nome, col in tabela.esquema_completo.items()}
                for r in dados["registros"]
            ]
            tabela.arvore = Arvore.de_lista(registros)
            proximo_id = dados["proximo_id"]
            maior_id = max((r["id"] for r in registros), default=0)
            if not isinstance(proximo_id, int) or proximo_id <= maior_id:
                raise ErroIffarql(f"proximo_id invalido na tabela '{tabela.nome}'")
            tabela.proximo_id = proximo_id
        except (KeyError, TypeError, ValueError) as erro:
            raise ErroIffarql(f"estrutura de tabela invalida no arquivo: {erro!r}")
        return tabela
