from iffarql.banco import Banco
from iffarql.erros import ErroIffarql
from iffarql.expressoes import Atribuicao, Coluna, Condicao
from iffarql.lexer import tokenizar
from iffarql.terminal import tabelar
from iffarql.tipos import obter_tipo

COMANDOS: dict[str, type["Comando"]] = {}

class Comando:
    palavra = ""
    sintaxe = ""
    altera_dados = False

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls.palavra:
            COMANDOS[cls.palavra] = cls

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "Comando":
        # tokens depois da palavra reservada -> comando pronto
        raise NotImplementedError

    def executar(self, bd: Banco) -> str:
        # roda e devolve o texto a exibir no terminal
        raise NotImplementedError


# Funcoes auxiliares

def _um_nome(tokens: list[str], palavra: str) -> str:
    if len(tokens) != 1:
        raise ErroIffarql(f"{palavra} espera apenas um nome")
    return tokens[0]

def _entre_parenteses(tokens: list[str], palavra: str) -> list[str]:
    if len(tokens) < 2 or tokens[0] != "(" or tokens[-1] != ")":
        raise ErroIffarql(f"{palavra}: valores precisam vir entre parenteses")
    conteudo = tokens[1:-1]
    if "(" in conteudo or ")" in conteudo:
        raise ErroIffarql(f"{palavra}: parenteses aninhados nao sao aceitos")
    return conteudo

def _ler_onde(tokens: list[str]) -> Condicao | None:
    if not tokens:
        return None
    if tokens[0] != "ONDE":
        raise ErroIffarql(f"esperado ONDE, encontrado '{tokens[0]}'")
    if len(tokens) != 4:
        raise ErroIffarql("ONDE espera <coluna> <comparador> <valor>")
    return Condicao(tokens[1], tokens[2], tokens[3])

def _separar_onde(tokens: list[str]) -> tuple[list[str], list[str]]:
    if "ONDE" not in tokens:
        return tokens, []
    corte = tokens.index("ONDE")
    return tokens[:corte], tokens[corte:]


# Comandos

class CriaTabela(Comando):
    palavra = "CRIATABELA"
    sintaxe = "<tabela> ( <coluna> <TIPO> [INTEIRO CHAVESTRANGEIRA <tabela>] ... )"
    altera_dados = True

    def __init__(self, nome: str, colunas: list[Coluna]) -> None:
        self.nome = nome
        self.colunas = colunas

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "CriaTabela":
        if not tokens:
            raise ErroIffarql("CRIATABELA espera o nome da tabela")
        nome, resto = tokens[0], _entre_parenteses(tokens[1:], "CRIATABELA")
        colunas: list[Coluna] = []
        i = 0
        while i < len(resto):
            if i + 1 >= len(resto):
                raise ErroIffarql(f"coluna '{resto[i]}' esta sem tipo")
            coluna, tipo, i = resto[i], obter_tipo(resto[i + 1]), i + 2
            estrangeira = None
            if i < len(resto) and resto[i] == "CHAVESTRANGEIRA":
                if i + 1 >= len(resto):
                    raise ErroIffarql("CHAVESTRANGEIRA espera o nome da tabela referenciada")
                estrangeira, i = resto[i + 1], i + 2
            colunas.append(Coluna(coluna, tipo, estrangeira))
        if not colunas:
            raise ErroIffarql("CRIATABELA espera pelo menos uma coluna")
        return cls(nome, colunas)

    def executar(self, bd: Banco) -> str:
        bd.criar_tabela(self.nome, self.colunas)
        return f"tabela '{self.nome}' criada"

class ApagaTabela(Comando):
    palavra = "APAGATABELA"
    sintaxe = "<tabela>"
    altera_dados = True

    def __init__(self, nome: str) -> None:
        self.nome = nome

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "ApagaTabela":
        return cls(_um_nome(tokens, "APAGATABELA"))

    def executar(self, bd: Banco) -> str:
        bd.apagar_tabela(self.nome)
        return f"tabela '{self.nome}' apagada"

class Inserir(Comando):
    palavra = "INSERIREM"
    sintaxe = "<tabela> VALOR ( <valor> ... )"
    altera_dados = True

    def __init__(self, nome: str, valores: list[str]) -> None:
        self.nome = nome
        self.valores = valores

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "Inserir":
        if len(tokens) < 2 or tokens[1] != "VALOR":
            raise ErroIffarql("falta a palavra VALOR")
        return cls(tokens[0], _entre_parenteses(tokens[2:], "INSERIREM"))

    def executar(self, bd: Banco) -> str:
        return f"registro {bd.inserir(self.nome, self.valores)} inserido em '{self.nome}'"

class Atualizar(Comando):
    palavra = "ATUALIZATABELA"
    sintaxe = "<tabela> COM <coluna> = <valor> [COM ...] [ONDE <coluna> <op> <valor>]"
    altera_dados = True

    def __init__(self, nome: str, atribuicoes: list[Atribuicao], condicao: Condicao | None) -> None:
        self.nome = nome
        self.atribuicoes = atribuicoes
        self.condicao = condicao

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "Atualizar":
        if len(tokens) < 2 or tokens[1] != "COM":
            raise ErroIffarql("falta a palavra COM")
        nome = tokens[0]
        atribuicoes_brutas, onde = _separar_onde(tokens[1:])
        blocos: list[list[str]] = []
        for token in atribuicoes_brutas:
            if token == "COM":
                blocos.append([])
            else:
                blocos[-1].append(token)
        atribuicoes = []
        for bloco in blocos:
            if len(bloco) < 3 or bloco[1] != "=":
                raise ErroIffarql(f"atribuicao invalida em COM {' '.join(bloco)}")
            atribuicoes.append(Atribuicao(bloco[0], tuple(bloco[2:])))
        return cls(nome, atribuicoes, _ler_onde(onde))

    def executar(self, bd: Banco) -> str:
        total = bd.atualizar(self.nome, self.atribuicoes, self.condicao)
        return f"{total} registro(s) atualizado(s) em '{self.nome}'"

class ApagaDados(Comando):
    palavra = "APAGADADOSDE"
    sintaxe = "<tabela> [ONDE <coluna> <op> <valor>]"
    altera_dados = True

    def __init__(self, nome: str, condicao: Condicao | None) -> None:
        self.nome = nome
        self.condicao = condicao

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "ApagaDados":
        if not tokens:
            raise ErroIffarql("APAGADADOSDE espera o nome da tabela")
        return cls(tokens[0], _ler_onde(tokens[1:]))

    def executar(self, bd: Banco) -> str:
        total = bd.apagar_dados(self.nome, self.condicao)
        return f"{total} registro(s) apagado(s) de '{self.nome}'"

class MostraDados(Comando):
    palavra = "MOSTRADADOSDE"
    sintaxe = "<tabela> [ONDE <coluna> <op> <valor>]"

    def __init__(self, nome: str, condicao: Condicao | None) -> None:
        self.nome = nome
        self.condicao = condicao

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "MostraDados":
        if not tokens:
            raise ErroIffarql("MOSTRADADOSDE espera o nome da tabela")
        return cls(tokens[0], _ler_onde(tokens[1:]))

    def executar(self, bd: Banco) -> str:
        tabela = bd.obter(self.nome)
        return tabelar(tabela.colunas, tabela.selecionar(self.condicao))

class SalvarBD(Comando):
    palavra = "SALVARBD"
    sintaxe = "<arquivo>"

    def __init__(self, arquivo: str) -> None:
        self.arquivo = arquivo

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "SalvarBD":
        return cls(_um_nome(tokens, "SALVARBD"))

    def executar(self, bd: Banco) -> str:
        bd.salvar(self.arquivo)
        return f"banco salvo em '{self.arquivo}'"

class CarregarBD(Comando):
    palavra = "CARREGARBD"
    sintaxe = "<arquivo>"
    altera_dados = True

    def __init__(self, arquivo: str) -> None:
        self.arquivo = arquivo

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "CarregarBD":
        return cls(_um_nome(tokens, "CARREGARBD"))

    def executar(self, bd: Banco) -> str:
        bd.carregar(self.arquivo)
        return f"banco '{self.arquivo}' carregado ({len(bd.tabelas)} tabela(s))"

class CarregarIffarql(Comando):
    palavra = "CARREGARIFFARQL"
    sintaxe = "<arquivo.txt>"
    altera_dados = True

    def __init__(self, arquivo: str) -> None:
        self.arquivo = arquivo

    @classmethod
    def de_tokens(cls, tokens: list[str]) -> "CarregarIffarql":
        return cls(_um_nome(tokens, "CARREGARIFFARQL"))

    def executar(self, bd: Banco) -> str:
        try:
            with open(self.arquivo, encoding="utf-8") as f:
                linhas = f.readlines()
        except OSError as erro:
            raise ErroIffarql(f"nao foi possivel ler '{self.arquivo}': {erro}")
        executados = 0
        with bd.transacao():
            for numero, linha in enumerate(linhas, 1):
                if not linha.strip():
                    continue
                try:
                    interpretar(linha).executar(bd)
                except ErroIffarql as erro:
                    raise ErroIffarql(f"linha {numero} de '{self.arquivo}': {erro}")
                executados += 1
        return f"{executados} comando(s) executado(s) de '{self.arquivo}'"

def interpretar(linha: str) -> Comando:
    tokens = tokenizar(linha)
    if not tokens:
        raise ErroIffarql("comando vazio")
    try:
        classe = COMANDOS[tokens[0]]
    except KeyError:
        raise ErroIffarql(f"comando '{tokens[0]}' nao existe - digite AJUDA")
    try:
        return classe.de_tokens(tokens[1:])
    except ErroIffarql as erro:
        raise ErroIffarql(f"{erro}\n  sintaxe: {classe.palavra} {classe.sintaxe}")