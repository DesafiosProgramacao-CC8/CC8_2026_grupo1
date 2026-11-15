import re
import os
import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple, Protocol
from urllib.parse import quote, unquote

from iffarql.expressoes import Atribuicao, Condicao
from iffarql.banco import Banco
from iffarql.comandos import interpretar


class ErroChat(Exception):
    def __init__(self, categoria: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.categoria = categoria
        self.mensagem = mensagem


class Contato(NamedTuple):
    id: int
    apelido: str


class Perfil(NamedTuple):
    nome: str
    apelido: str
    idade: int


class Mensagem(NamedTuple):
    remetente: int
    texto: str
    data: str
    hora: int
    minuto: int


class Repositorio(Protocol):
    # usuário

    def registrar(self, nome: str, apelido: str, nascimento: str, senha: str) -> None:
        """8. Erro: ERROREGISTRO (apelido em uso, data inválida)."""
        ...

    def autenticar(self, apelido: str, senha: str) -> int:
        """16. Devolve o id. Erro: ERROAUTENTICACAO."""
        ...

    def perfil(self, id: int) -> Perfil:
        """8192. Erro: ERROVERPERFIL."""
        ...

    def atualizar_perfil(self, id: int, nome: str, nascimento: str, senha: str) -> None:
        """16384. Senha só confere, não muda. Erro: ERROATUALIZARPERFIL."""
        ...

    # amizade

    def amigos(self, id: int) -> list[Contato]:
        """64 tipo 1. Só amizades aceitas."""
        ...

    def pedir_amizade(self, solicitante: int, alvo: int) -> None:
        """256. Erro: ERROCONEXAO (alvo inexistente, ele mesmo, já são amigos)."""
        ...

    def pedidos_pendentes(self, id: int) -> list[int]:
        """Quem pediu amizade a id sem resposta (reenviar 257 no login)."""
        ...

    def responder_amizade(self, quem_responde: int, solicitante: int, aceita: bool) -> None:
        """258. Aceita ou apaga o pedido. Erro: ERROCONEXAO (sem pedido pendente)."""
        ...

    def alternar_silencio(self, id: int, amigo: int) -> None:
        """512. Erro: ERROMENSAGENS (não são amigos)."""
        ...

    # dm

    def notificacoes(self, id: int) -> list[int]:
        """128. Amigos com mensagem não lida, menos os silenciados."""
        ...

    def enviar_privada(self, remetente: int, destinatario: int, texto: str,
                       quando: datetime) -> None:
        """2048. Erro: ERROENVIARMENSAGEM (não são amigos)."""
        ...

    def novas_privadas(self, id: int, amigo: int) -> list[Mensagem]:
        """1024. Mensagens do amigo ainda não entregues; marca como lidas. Erro: ERROMENSAGENS."""
        ...

    def historico(self, id: int, amigo: int) -> list[Mensagem]:
        """4096. Conversa inteira; marca como lidas. Erro: ERROHISTORICOMENSAGENS."""
        ...

ESQUEMA = Path(__file__).with_name("esquema.iffarql")
_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

def _texto(valor: str) -> str:
    """Python -> IFFARQL: codifica e põe entre aspas."""
    return '"' + quote(valor, safe="") + '"'


def _de_texto(valor: str) -> str:
    """IFFARQL -> Python (o banco já devolve sem as aspas)."""
    return unquote(valor)


def _validar_nascimento(texto: str, hoje: date, categoria: str) -> str:
    """Devolve a data pronta para o banco ou levanta ErroChat(categoria)."""
    m = _DATA.fullmatch(texto)
    if not m:
        raise ErroChat(categoria, "data deve estar no formato DD/MM/AAAA")
    dia, mes, ano = int(m[1]), int(m[2]), int(m[3])
    try:
        nascimento = date(ano, mes, dia)        # recusa 31/02, 00/13...
    except ValueError:
        raise ErroChat(categoria, "data inexistente")
    if (dia, mes) == (29, 2):                   # o T2 não conhece ano bissexto
        raise ErroChat(categoria, "29/02 nao e suportado pelo banco")
    if nascimento >= hoje:
        raise ErroChat(categoria, "data de nascimento precisa estar no passado")
    return f'"{texto}"'


def _idade(nascimento: tuple[int, int, int], hoje: date) -> int:
    dia, mes, ano = nascimento
    # True vale 1: tira um ano se o aniversário ainda não chegou
    return hoje.year - ano - ((hoje.month, hoje.day) < (mes, dia))


def _usuario_por_id(bd: Banco, id: int) -> dict | None:
    achados = bd.selecionar("usuario", Condicao("id", "==", str(id)))
    return achados[0] if achados else None


def _usuario_por_apelido(bd: Banco, apelido: str) -> dict | None:
    achados = bd.selecionar("usuario", Condicao("apelido", "==", _texto(apelido)))
    return achados[0] if achados else None


def _por_id(id: int) -> Condicao:
    """ONDE id == <id>: usado para atualizar/apagar exatamente uma linha."""
    return Condicao("id", "==", str(id))


def _linha_amizade(bd: Banco, dono: int, outro: int) -> dict | None:
    """A linha (dono, outro). O ONDE só aceita uma condição: filtra o resto em Python."""
    for linha in bd.selecionar("amizade", Condicao("id_usuario_1", "==", str(dono))):
        if linha["id_usuario_2"] == outro:
            return linha
    return None


def _novo_valor(coluna: str, valor: bool) -> Atribuicao:
    """COM <coluna> = true/false"""
    return Atribuicao(coluna, ("true" if valor else "false",))


def _amizade_aceita(bd: Banco, id: int, amigo: int, categoria: str) -> tuple[dict, dict]:
    """(minha linha, linha dele), ou ErroChat(categoria) se não forem amigos."""
    minha = _linha_amizade(bd, id, amigo)
    if minha is None or not minha["aceita"]:
        raise ErroChat(categoria, "voces nao sao amigos")
    return minha, _linha_amizade(bd, amigo, id)


def _conversas_da_linha(bd: Banco, linha: dict) -> list[dict]:
    """Mensagens enviadas pelo dono da linha, já em ordem de id."""
    return bd.selecionar("conversa", Condicao("id_amizade", "==", str(linha["id"])))


def _para_mensagem(conversa: dict, remetente: int) -> Mensagem:
    dia, mes, ano = conversa["data"]               # o T2 devolve DATA como tupla
    return Mensagem(remetente, _de_texto(conversa["mensagem"]),
                    f"{dia:02d}/{mes:02d}/{ano:04d}", conversa["hora"], conversa["minuto"])


def _marcar_lidas(bd: Banco, minha: dict, recebidas: list[dict]) -> None:
    """Zera a notificação e avança o cursor até a última mensagem recebida."""
    mudancas = [_novo_valor("ha_notificacao", False)]
    if recebidas:
        mudancas.append(Atribuicao("ultima_lida", (str(recebidas[-1]["id"]),)))
    bd.atualizar("amizade", mudancas, _por_id(minha["id"]))


class RepositorioIffarql(Repositorio):
    def __init__(self, caminho, hoje: Callable[[], date] = date.today) -> None:
        self._caminho = str(caminho) #T2 trabalha com str
        self._hoje = hoje #chama a function a cada uso
        self._fila = queue.Queue()
        self._bd = Banco() #só o worker toca nele
        self._trabalhador = threading.Thread(target=self._consumir, name="trabalhador-bd", daemon=True)
        self._trabalhador.start()
        self._executar(self._abrir) #abertura passa pela fila


    def _consumir(self) -> None:
        while True:
            item = self._fila.get() #fica em repouso até chegar pedido
            if item is None: #sinal do fechar()
                break
            funcao, altera, futuro = item
            try:
                if altera:
                    with self._bd.transacao():   # snapshot + rollback + salvar
                        resultado = funcao(self._bd)
                else:
                    resultado = funcao(self._bd)  # leitura: nada a desfazer nem salvar
            except Exception as erro:
                futuro.set_exception(erro)
            else:
                futuro.set_result(resultado)


    def _executar(self, funcao, altera: bool = True):
        futuro = Future()
        self._fila.put((funcao, altera, futuro))
        return futuro.result()


    def _abrir(self, bd: Banco) -> None:
        if os.path.exists(self._caminho):
            bd.carregar(self._caminho)
            return
        os.makedirs(os.path.dirname(self._caminho) or ".", exist_ok=True)
        with open(ESQUEMA, encoding="utf-8") as f:
            for linha in f:
                if linha.strip():
                    interpretar(linha).executar(bd)
        bd.salvar(self._caminho)


    def fechar(self) -> None:
        self._fila.put(None)
        self._trabalhador.join()


    def registrar(self, nome: str, apelido: str, nascimento: str, senha: str) -> None:
        if not nome.strip() or not apelido.strip() or not senha:
            raise ErroChat("ERROREGISTRO", "nome, apelido e senha sao obrigatorios")
        data = _validar_nascimento(nascimento, self._hoje(), "ERROREGISTRO")

        def operacao(bd: Banco) -> None:
            # checar e inserir na MESMA tarefa: ninguém registra "ana" no meio
            if _usuario_por_apelido(bd, apelido) is not None:
                raise ErroChat("ERROREGISTRO", "apelido ja esta em uso")
            bd.inserir("usuario", [_texto(nome), _texto(apelido), data, _texto(senha)])

        self._executar(operacao)

    def autenticar(self, apelido: str, senha: str) -> int:
        def operacao(bd: Banco) -> int:
            usuario = _usuario_por_apelido(bd, apelido)
            if usuario is None or _de_texto(usuario["senha"]) != senha:
                raise ErroChat("ERROAUTENTICACAO", "apelido ou senha incorretos")
            return usuario["id"]

        return self._executar(operacao, altera=False)

    def perfil(self, id: int) -> Perfil:
        hoje = self._hoje()

        def operacao(bd: Banco) -> Perfil:
            usuario = _usuario_por_id(bd, id)
            if usuario is None:
                raise ErroChat("ERROVERPERFIL", "usuario nao existe")
            return Perfil(                       # monta aqui dentro: o dict não sai da fila
                _de_texto(usuario["nome_completo"]),
                _de_texto(usuario["apelido"]),
                _idade(usuario["data_nascimento"], hoje),
            )

        return self._executar(operacao, altera=False)

    def atualizar_perfil(self, id: int, nome: str, nascimento: str, senha: str) -> None:
        if not nome.strip():
            raise ErroChat("ERROATUALIZARPERFIL", "nome e obrigatorio")
        data = _validar_nascimento(nascimento, self._hoje(), "ERROATUALIZARPERFIL")

        def operacao(bd: Banco) -> None:
            usuario = _usuario_por_id(bd, id)
            if usuario is None or _de_texto(usuario["senha"]) != senha:
                raise ErroChat("ERROATUALIZARPERFIL", "senha incorreta")
            bd.atualizar(
                "usuario",
                [Atribuicao("nome_completo", (_texto(nome),)),
                 Atribuicao("data_nascimento", (data,))],
                Condicao("id", "==", str(id)),
            )

        self._executar(operacao)


        # amizade

    def pedir_amizade(self, solicitante: int, alvo: int) -> None:
        if solicitante == alvo:
            raise ErroChat("ERROCONEXAO", "nao e possivel pedir amizade a si mesmo")

        def operacao(bd: Banco) -> None:
            if _usuario_por_id(bd, alvo) is None:
                raise ErroChat("ERROCONEXAO", "usuario nao existe")
            if _linha_amizade(bd, solicitante, alvo) is not None:
                raise ErroChat("ERROCONEXAO", "ja existe amizade ou pedido entre os dois")
            #                       id_usuario_1      id_usuario_2      bloq.    notif.   aceita  ult_lida
            bd.inserir("amizade", [str(solicitante), str(alvo),        "false", "false", "false", "0"])
            bd.inserir("amizade", [str(alvo),        str(solicitante), "false", "true",  "false", "0"])

        self._executar(operacao)

    def pedidos_pendentes(self, id: int) -> list[int]:
        def operacao(bd: Banco) -> list[int]:
            return [
                linha["id_usuario_2"]
                for linha in bd.selecionar("amizade", Condicao("id_usuario_1", "==", str(id)))
                if not linha["aceita"] and linha["ha_notificacao"]
            ]

        return self._executar(operacao, altera=False)

    def responder_amizade(self, quem_responde: int, solicitante: int, aceita: bool) -> None:
        def operacao(bd: Banco) -> None:
            minha = _linha_amizade(bd, quem_responde, solicitante)
            # só o alvo tem ha_notificacao=true: impede o solicitante de se aceitar
            if minha is None or minha["aceita"] or not minha["ha_notificacao"]:
                raise ErroChat("ERROCONEXAO", "nao ha pedido de amizade pendente")
            dele = _linha_amizade(bd, solicitante, quem_responde)
            if aceita:
                bd.atualizar("amizade",
                             [_novo_valor("aceita", True), _novo_valor("ha_notificacao", False)],
                             _por_id(minha["id"]))
                bd.atualizar("amizade", [_novo_valor("aceita", True)], _por_id(dele["id"]))
            else:
                bd.apagar_dados("amizade", _por_id(minha["id"]))
                bd.apagar_dados("amizade", _por_id(dele["id"]))

        self._executar(operacao)

    def amigos(self, id: int) -> list[Contato]:
        def operacao(bd: Banco) -> list[Contato]:
            contatos = []
            for linha in bd.selecionar("amizade", Condicao("id_usuario_1", "==", str(id))):
                if linha["aceita"]:
                    amigo = _usuario_por_id(bd, linha["id_usuario_2"])
                    contatos.append(Contato(amigo["id"], _de_texto(amigo["apelido"])))
            return contatos

        return self._executar(operacao, altera=False)

    def alternar_silencio(self, id: int, amigo: int) -> None:
        def operacao(bd: Banco) -> None:
            minha = _linha_amizade(bd, id, amigo)
            if minha is None or not minha["aceita"]:
                raise ErroChat("ERROMENSAGENS", "voces nao sao amigos")
            bd.atualizar("amizade", [_novo_valor("bloqueado", not minha["bloqueado"])],
                         _por_id(minha["id"]))

        self._executar(operacao)

        # dm

    def enviar_privada(self, remetente: int, destinatario: int, texto: str,
                       quando: datetime) -> None:
        def operacao(bd: Banco) -> None:
            minha, dele = _amizade_aceita(bd, remetente, destinatario, "ERROENVIARMENSAGEM")
            bd.inserir("conversa", [str(minha["id"]), f'"{quando:%d/%m/%Y}"',
                                    str(quando.hour), str(quando.minute), _texto(texto)])
            # avisa o destinatário (mesmo silenciado: quem filtra é notificacoes)
            bd.atualizar("amizade", [_novo_valor("ha_notificacao", True)], _por_id(dele["id"]))

        self._executar(operacao)

    def notificacoes(self, id: int) -> list[int]:
        def operacao(bd: Banco) -> list[int]:
            return [
                linha["id_usuario_2"]
                for linha in bd.selecionar("amizade", Condicao("id_usuario_1", "==", str(id)))
                if linha["aceita"] and linha["ha_notificacao"] and not linha["bloqueado"]
            ]

        return self._executar(operacao, altera=False)

    def novas_privadas(self, id: int, amigo: int) -> list[Mensagem]:
        def operacao(bd: Banco) -> list[Mensagem]:
            minha, dele = _amizade_aceita(bd, id, amigo, "ERROMENSAGENS")
            novas = [c for c in _conversas_da_linha(bd, dele) if c["id"] > minha["ultima_lida"]]
            _marcar_lidas(bd, minha, novas)
            return [_para_mensagem(c, amigo) for c in novas]

        return self._executar(operacao)

    def historico(self, id: int, amigo: int) -> list[Mensagem]:
        def operacao(bd: Banco) -> list[Mensagem]:
            minha, dele = _amizade_aceita(bd, id, amigo, "ERROHISTORICOMENSAGENS")
            enviadas = _conversas_da_linha(bd, minha)
            recebidas = _conversas_da_linha(bd, dele)
            _marcar_lidas(bd, minha, recebidas)
            todas = [(c, id) for c in enviadas] + [(c, amigo) for c in recebidas]
            todas.sort(key=lambda par: par[0]["id"])     # ordem real de chegada
            return [_para_mensagem(c, quem) for c, quem in todas]

        return self._executar(operacao)

