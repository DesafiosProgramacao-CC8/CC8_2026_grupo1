from datetime import datetime
from typing import NamedTuple, Protocol


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
