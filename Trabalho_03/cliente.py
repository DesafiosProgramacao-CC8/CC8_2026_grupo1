import socket
import sys
import threading
import time
from datetime import datetime
from getpass import getpass
from typing import NamedTuple

from senha import fnv1a, senha_valida


CONECTAR, CONECTADO, PING, PONG = 2, 3, 4, 5
REGISTRAR, REGISTRADO = 8, 9
AUTENTICAR, AUTENTICADO = 16, 17
DESCONECTAR, DESCONECTADO = 32, 33
LISTARUSUARIOS, USUARIOS = 64, 65
VERIFICARNOTIFICACAO, NOTIFICACOES = 128, 129
NOVAAMIZADE, PEDIDOAMIZADE, CONEXAOAMIZADE, RESPOSTAAMIZADE = 256, 257, 258, 259
ALTERARSILENCIAMENTO, SILENCIARALTERADO = 512, 513
PEGARMENSAGENS, MENSAGENS = 1024, 1025
ENVIARMENSAGEM, MENSAGEMENVIADA = 2048, 2049
PEGARHISTORICOMENSAGENS, HISTORICOMENSAGENS = 4096, 4097
VERPERFIL, PERFIL = 8192, 8193
ATUALIZARPERFIL, PERFILATUALIZADO = 16384, 16385
ERRO = 32768

ONLINE, AMIGOS = "0", "1" 
VERDADEIRO, FALSO = "VERDADEIRO", "FALSO"

PORTA = 42000
TIMEOUT = 5      
INTERVALO = 2 
TAMANHO_MENSAGEM = 500


def montar(codigo: int, *campos: str) -> bytes:
    return ("|".join([str(codigo), *campos]) + "|#\n").encode("utf-8")


def ler(arquivo) -> list[str]:
    linha = arquivo.readline()
    if not linha:
        raise EOFError("servidor fechou a conexão")
    texto = linha.decode("utf-8", errors="replace").rstrip("\r\n")
    if texto.endswith("#"):
        texto = texto[:-1]
    if texto.endswith("|"):
        texto = texto[:-1]
    return texto.split("|")


def campo_valido(texto: str) -> bool:
    return "|" not in texto and "\n" not in texto and "\r" not in texto


class Mensagem(NamedTuple):
    remetente: str
    texto: str
    data: str
    hora: str
    minuto: str


def _blocos(campos: list[str], tamanho: int) -> list[list[str]]:
    inteiros = len(campos) - len(campos) % tamanho 
    return [campos[i:i + tamanho] for i in range(0, inteiros, tamanho)]


def ler_mensagens(campos: list[str]) -> list[Mensagem]:
    return [Mensagem(r, t, d, h, m) for r, t, d, h, m in _blocos(campos, 5)]


def ler_historico(campos: list[str]) -> list[Mensagem]:
    return [Mensagem(r, t, d, h, m) for r, d, h, m, t in _blocos(campos, 5)]


class ErroServidor(Exception):
    def __init__(self, categoria: str, mensagem: str) -> None:
        super().__init__(f"{categoria}: {mensagem}")
        self.categoria = categoria
        self.mensagem = mensagem


class ConexaoPerdida(Exception):
    """Timeout, socket fechado ou erro de rede. O cliente volta a DESCONECTADO."""


class Conexao:
    def __init__(self, host: str, porta: int = PORTA, timeout: float = TIMEOUT,
                 notificar=None) -> None:
        self.notificar = notificar or (lambda quadro: None)
        self._lock = threading.Lock()
        self._sock = socket.create_connection((host, porta), timeout=timeout)
        self._sock.settimeout(timeout)
        self._arquivo = self._sock.makefile("rb")
        self.pedir(CONECTAR, esperado=CONECTADO)

    def pedir(self, codigo: int, *campos: str, esperado: int) -> list[str]:
        with self._lock:
            self._enviar(montar(codigo, *campos))
            return self._esperar(esperado)

    def enviar_sem_resposta(self, codigo: int, *campos: str) -> None:
        with self._lock:
            self._enviar(montar(codigo, *campos))
            self._enviar(montar(PING))
            self._esperar(PONG)

    def fechar(self) -> None:
        if self._sock is None:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        self._sock = None

    def _enviar(self, quadro: bytes) -> None:
        if self._sock is None:
            raise ConexaoPerdida("conexão fechada")
        try:
            self._sock.sendall(quadro)
        except OSError as erro:
            self.fechar()
            raise ConexaoPerdida(str(erro)) from erro

    def _esperar(self, esperado: int) -> list[str]:
        while True:
            try:
                quadro = ler(self._arquivo)
            except (OSError, EOFError) as erro: 
                self.fechar()
                raise ConexaoPerdida(str(erro)) from erro
            codigo = int(quadro[0]) if quadro[0].isdigit() else -1
            if codigo == esperado:
                return quadro[1:]
            if codigo == ERRO:
                categoria = quadro[1] if len(quadro) > 1 else "?"
                mensagem = quadro[2] if len(quadro) > 2 else ""
                raise ErroServidor(categoria, mensagem)
            self.notificar(quadro)

class Cliente:
    def __init__(self, host_padrao: str = "localhost") -> None:
        self.host_padrao = host_padrao
        self.conexao: Conexao | None = None
        self.id: str | None = None
        self.apelido = ""
        self.apelidos: dict[str, str] = {}  
        self.novas: set[str] = set()     
        self.pedidos: set[str] = set()  
        self.respostas: list[tuple[str, bool]] = [] 
        self.conversa: str | None = None 


    def executar(self) -> None:
        print("=== IFFARCHAT ===")
        while True:
            try:
                if self.conexao is None:
                    self.tela_desconectado()
                elif self.id is None:
                    self.tela_conectado()
                else:
                    self.tela_logado()
            except ErroServidor as erro:
                print(f"\nerro do servidor ({erro.categoria}): {erro.mensagem}")
            except ConexaoPerdida:
                self._perdeu_conexao()
            except (KeyboardInterrupt, EOFError):
                print("\naté mais!")
                self._encerrar()
                return

    def tela_desconectado(self) -> None:
        escolha = self._menu("DESCONECTADO", ["Conectar"], "Sair")
        if escolha == "0":
            self._encerrar()
            raise SystemExit
        if escolha == "1":
            host = input(f"host [{self.host_padrao}]: ").strip() or self.host_padrao
            try:
                self.conexao = Conexao(host, notificar=self._notificar)
            except OSError as erro:
                print(f"não foi possível conectar a {host}:{PORTA} ({erro})")
                return
            print(f"conectado a {host}:{PORTA}")

    def tela_conectado(self) -> None:
        escolha = self._menu("CONECTADO", ["Registrar", "Entrar"], "Desconectar")
        if escolha == "1":
            self.registrar()
        elif escolha == "2":
            self.entrar()
        elif escolha == "0":
            self._encerrar()

    def tela_logado(self) -> None:
        print("\n" + self._barra())
        opcoes = [
            ("Chat geral", lambda: self.conversar("")),
            ("Quem está online", lambda: self.listar(ONLINE)),
            ("Meus amigos", lambda: self.listar(AMIGOS)),
            ("Pedidos de amizade", self.responder_pedidos),
            ("Adicionar amigo", self.adicionar_amigo),
            ("Conversa privada", self.conversa_privada),
            ("Silenciar/dessilenciar amigo", self.silenciar),
            ("Ver perfil", self.ver_perfil),
            ("Editar meu perfil", self.editar_perfil),
        ]
        escolha = self._menu(f"LOGADO como {self.apelido}", [nome for nome, _ in opcoes], "Logoff")
        if escolha == "0":
            self.logoff()
        elif escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            opcoes[int(escolha) - 1][1]()


    def registrar(self) -> None:
        nome = self._campo("nome completo")
        apelido = self._campo("apelido")
        nascimento = self._campo("nascimento (DD/MM/AAAA)")
        print("(a senha não aparece enquanto você digita; digite 6 letras ou números e aperte Enter)")
        while True:
            senha = getpass("senha: ")
            if senha_valida(senha):
                break
            if len(senha) != 6:
                print(f"você digitou {len(senha)} caracteres; a senha precisa ter exatamente 6")
            else:
                print("a senha só pode ter letras sem acento e números")
        self._pedir(REGISTRAR, nome, apelido, nascimento, fnv1a(senha), esperado=REGISTRADO)
        print("registrado! agora use 'Entrar'.")

    def entrar(self) -> None:
        apelido = self._campo("apelido")
        senha = getpass("senha: ")
        campos = self._pedir(AUTENTICAR, apelido, fnv1a(senha), esperado=AUTENTICADO)
        if not campos:
            raise ErroServidor("ERROAUTENTICACAO", "servidor não informou o id")
        self.id = campos[0]
        self.apelido = apelido
        self.apelidos[self.id] = apelido
        threading.Thread(target=self._verificar_periodicamente, daemon=True).start()
        print(f"bem-vindo, {apelido} (id {self.id})")

    def logoff(self) -> None:
        meu_id, self.id = self.id, None 
        try:
            self._pedir(DESCONECTAR, meu_id, esperado=DESCONECTADO)
        except ConexaoPerdida:
            pass 
        self._encerrar()
        print("logoff feito")


    def listar(self, tipo: str) -> list[str]:
        campos = self._pedir(LISTARUSUARIOS, self.id, tipo, esperado=USUARIOS)
        ids = []
        for id, apelido in _blocos(campos, 2):
            self.apelidos[id] = apelido
            ids.append(id)
        titulo = "online" if tipo == ONLINE else "amigos"
        if not ids:
            print(f"ninguém {titulo}" if tipo == ONLINE else "você ainda não tem amigos")
        else:
            print(f"{titulo}:")
            for id in ids:
                print(f"  {id:>4}  {self.apelidos[id]}")
        return ids

    def adicionar_amigo(self) -> None:
        self.listar(ONLINE)
        alvo = self._campo("id do usuário (vazio para cancelar)", obrigatorio=False)
        if not alvo:
            return
        self.conexao.enviar_sem_resposta(NOVAAMIZADE, self.id, alvo)
        print(f"pedido de amizade enviado para {self._nome(alvo)}")

    def responder_pedidos(self) -> None:
        if not self.pedidos:
            print("nenhum pedido de amizade pendente")
            return
        for solicitante in sorted(self.pedidos):
            resposta = input(f"{self._nome(solicitante)} quer ser seu amigo. aceitar? [s/n/pular] ").strip().lower()
            if resposta in ("s", "n"):
                aceita = VERDADEIRO if resposta == "s" else FALSO
                self.conexao.enviar_sem_resposta(CONEXAOAMIZADE, self.id, solicitante, aceita)
                self.pedidos.discard(solicitante)
                print("aceito" if resposta == "s" else "recusado")

    def silenciar(self) -> None:
        if not self.listar(AMIGOS):
            return
        amigo = self._campo("id do amigo (vazio para cancelar)", obrigatorio=False)
        if not amigo:
            return
        self._pedir(ALTERARSILENCIAMENTO, self.id, amigo, esperado=SILENCIARALTERADO)
        print(f"silenciamento de {self._nome(amigo)} alterado")


    def ver_perfil(self) -> None:
        alvo = self._campo(f"id do usuário [{self.id}]", obrigatorio=False) or self.id
        campos = self._pedir(VERPERFIL, alvo, esperado=PERFIL)
        if len(campos) < 4:
            print("resposta incompleta:", campos)
            return
        id, nome, apelido, idade = campos[:4]
        self.apelidos[id] = apelido
        print(f"id: {id}\nnome: {nome}\napelido: {apelido}\nidade: {idade}")

    def editar_perfil(self) -> None:
        nome = self._campo("novo nome completo")
        nascimento = self._campo("novo nascimento (DD/MM/AAAA)")
        senha = getpass("senha atual (para confirmar): ")
        self._pedir(ATUALIZARPERFIL, self.id, nome, nascimento, fnv1a(senha), esperado=PERFILATUALIZADO)
        print("perfil atualizado")

    def conversa_privada(self) -> None:
        if not self.listar(AMIGOS):
            return
        amigo = self._campo("id do amigo (vazio para cancelar)", obrigatorio=False)
        if amigo:
            self.conversar(amigo)

    def conversar(self, amigo: str) -> None:
        if amigo:
            print(f"--- conversa com {self._nome(amigo)} ---")
            campos = self._pedir(PEGARHISTORICOMENSAGENS, self.id, amigo, esperado=HISTORICOMENSAGENS)
            for mensagem in ler_historico(campos):
                print(self._formatar(mensagem))
            self.novas.discard(amigo)
        else:
            print("--- chat geral ---")
        print("(digite /sair para voltar ao menu)")
        self.conversa = amigo
        try:
            while True:
                texto = input()
                if texto == "/sair":
                    return
                if not texto.strip():
                    continue
                if not campo_valido(texto):
                    print("a mensagem não pode conter '|' nem quebra de linha")
                    continue
                if len(texto) > TAMANHO_MENSAGEM:
                    print(f"a mensagem deve ter no máximo {TAMANHO_MENSAGEM} caracteres")
                    continue
                self._pedir(ENVIARMENSAGEM, self.id, amigo, texto, esperado=MENSAGEMENVIADA)
                agora = datetime.now()
                print(self._formatar(Mensagem(self.id, texto, f"{agora:%d/%m/%Y}",
                                              str(agora.hour), str(agora.minute))))
        finally:
            self.conversa = None

    def _verificar_periodicamente(self) -> None:
        while True:
            time.sleep(INTERVALO)
            if self.id is None or self.conexao is None:
                return
            try:
                campos = self._pedir(VERIFICARNOTIFICACAO, self.id, esperado=NOTIFICACOES)
                self.novas = {id for id in campos if id}
                conversa = self.conversa
                if conversa is not None:
                    campos = self._pedir(PEGARMENSAGENS, self.id, conversa, esperado=MENSAGENS)
                    for mensagem in ler_mensagens(campos):
                        if mensagem.remetente != self.id: 
                            print(self._formatar(mensagem))
            except ErroServidor as erro:
                print(f"\n[servidor] {erro.categoria}: {erro.mensagem}")
            except ConexaoPerdida:
                if self.id is not None:
                    self._perdeu_conexao()
                    print("(pressione Enter)")
                return

    def _notificar(self, quadro: list[str]) -> None:
        codigo = quadro[0]
        if codigo == str(PEDIDOAMIZADE) and len(quadro) >= 2:
            self.pedidos.add(quadro[1])
            print(f"\n[pedido de amizade de {self._nome_cache(quadro[1])}]")
        elif codigo == str(RESPOSTAAMIZADE) and len(quadro) >= 3:
            aceitou = quadro[2] == VERDADEIRO
            self.respostas.append((quadro[1], aceitou))
            print(f"\n[{self._nome_cache(quadro[1])} {'aceitou' if aceitou else 'recusou'} sua amizade]")

    def _barra(self) -> str:
        partes = []
        if self.novas:
            partes.append("novas mensagens: " + ", ".join(self._nome(id) for id in sorted(self.novas)))
        if self.pedidos:
            partes.append(f"pedidos de amizade: {len(self.pedidos)}")
        if self.respostas:
            partes.append("respostas: " + ", ".join(
                f"{self._nome(id)} {'aceitou' if ok else 'recusou'}" for id, ok in self.respostas))
            self.respostas.clear()                 # mostrada uma vez
        return "[" + " | ".join(partes) + "]" if partes else "[sem notificações]"


    def _pedir(self, codigo: int, *campos: str, esperado: int) -> list[str]:
        if self.conexao is None:
            raise ConexaoPerdida("sem conexão")
        return self.conexao.pedir(codigo, *campos, esperado=esperado)

    def _nome(self, id: str) -> str:
        if id not in self.apelidos:
            try:
                campos = self._pedir(VERPERFIL, id, esperado=PERFIL)
                if len(campos) >= 3:
                    self.apelidos[id] = campos[2]
            except ErroServidor:
                pass
        return self._nome_cache(id)

    def _nome_cache(self, id: str) -> str:
        return self.apelidos.get(id, f"id {id}")

    def _formatar(self, m: Mensagem) -> str:
        quem = "eu" if m.remetente == self.id else self._nome(m.remetente)
        return f"[{m.data} {m.hora.zfill(2)}:{m.minuto.zfill(2)}] {quem}: {m.texto}"

    def _menu(self, titulo: str, opcoes: list[str], saida: str) -> str:
        print(f"\n--- {titulo} ---")
        for numero, opcao in enumerate(opcoes, 1):
            print(f"{numero}. {opcao}")
        print(f"0. {saida}")
        return input("> ").strip()

    def _campo(self, rotulo: str, obrigatorio: bool = True) -> str:
        while True:
            texto = input(f"{rotulo}: ").strip()
            if not texto and obrigatorio:
                print("campo obrigatório")
            elif not campo_valido(texto):
                print("não pode conter '|' nem quebra de linha")
            else:
                return texto

    def _perdeu_conexao(self) -> None:
        if self.conexao is not None:
            print("\nconexão com o servidor perdida")
        self._encerrar()

    def _encerrar(self) -> None:
        self.id = None
        self.conversa = None
        if self.conexao is not None:
            self.conexao.fechar()
            self.conexao = None
        self.novas.clear()
        self.pedidos.clear()
        self.respostas.clear()


if __name__ == "__main__":
    Cliente(sys.argv[1] if len(sys.argv) > 1 else "localhost").executar()
