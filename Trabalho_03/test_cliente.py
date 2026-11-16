import io
import socket
import threading

import pytest

from cliente import (
    CONECTAR, CONECTADO, PING, PONG, AUTENTICAR, AUTENTICADO, NOVAAMIZADE,
    Conexao, ConexaoPerdida, ErroServidor, Mensagem,
    campo_valido, ler, ler_historico, ler_mensagens, montar,
)


@pytest.mark.parametrize("codigo, campos, esperado", [
    (2, (), b"2|#\n"),
    (3, (), b"3|#\n"),
    (8, ("Fulano Ciclano", "fuciclano", "01/01/2001", "AAAArgAKAg=="),
     b"8|Fulano Ciclano|fuciclano|01/01/2001|AAAArgAKAg==|#\n"),
    (1024, ("12", ""), b"1024|12||#\n"),
    (2048, ("12", "", "Que chuvinha chata hein?"), b"2048|12||Que chuvinha chata hein?|#\n"),
    (258, ("45", "12", "VERDADEIRO"), b"258|45|12|VERDADEIRO|#\n"),
])
def test_montar_exemplos_do_enunciado(codigo, campos, esperado):
    assert montar(codigo, *campos) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    (b"3|#\n", ["3"]),
    (b"17|23|#\n", ["17", "23"]),
    (b"1024|12||#\n", ["1024", "12", ""]), 
    (b"65|12|beltrano|30|ciclano|321|deltrano|#\n",
     ["65", "12", "beltrano", "30", "ciclano", "321", "deltrano"]),
    (b"32768|ERROAUTENTICACAO|Senha inv\xc3\xa1lida|#\n", ["32768", "ERROAUTENTICACAO", "Senha inválida"]),
    (b"3|#\r\n", ["3"]),           
    (b"3#\n", ["3"]),      
])
def test_ler_exemplos_do_enunciado(bruto, esperado):
    assert ler(io.BytesIO(bruto)) == esperado


def test_ler_ida_e_volta():
    for campos in [("12", ""), ("a", "b", "c"), ("", ""), ("x",)]:
        assert ler(io.BytesIO(montar(99, *campos))) == ["99", *campos]


def test_ler_socket_fechado():
    with pytest.raises(EOFError):
        ler(io.BytesIO(b""))


@pytest.mark.parametrize("texto, valido", [
    ("oi, tudo bem?", True),
    ("C# é legal", True), 
    ("a|b", False),
    ("fim#\n", False),
    ("duas\nlinhas", False),
    ("retorno\r", False),
])
def test_campo_valido(texto, valido):
    assert campo_valido(texto) is valido


def test_ler_mensagens_exemplo_1025():
    quadro = ler(io.BytesIO(
        b"1025|24|O que foi aquela viagem?|02/02/2026|12|45|32|Cara, inexpl\xc3\xa1vel!! :@|02/02/2026|24|45"
        b"|32|Mas faria tudo novamente hahahaha|02/02/2026|12|46|#\n"))
    assert ler_mensagens(quadro[1:]) == [
        Mensagem("24", "O que foi aquela viagem?", "02/02/2026", "12", "45"),
        Mensagem("32", "Cara, inexplável!! :@", "02/02/2026", "24", "45"),
        Mensagem("32", "Mas faria tudo novamente hahahaha", "02/02/2026", "12", "46"),
    ]


def test_ler_historico_exemplo_4097():
    quadro = ler(io.BytesIO(
        b"4097|12|02/02/2026|12|44|Ol\xc3\xa1 prazer!|32|02/02/2026|12|44|Ol\xc3\xa1, prazer, como tu est\xc3\xa1?"
        b"|12|02/02/2026|12|45|Bem e tu?|32|02/02/2026|12|45|Bem tamb\xc3\xa9m.|#\n"))
    assert ler_historico(quadro[1:]) == [
        Mensagem("12", "Olá prazer!", "02/02/2026", "12", "44"),
        Mensagem("32", "Olá, prazer, como tu está?", "02/02/2026", "12", "44"),
        Mensagem("12", "Bem e tu?", "02/02/2026", "12", "45"),
        Mensagem("32", "Bem também.", "02/02/2026", "12", "45"),
    ]


def test_lista_vazia_e_bloco_incompleto():
    assert ler_mensagens([]) == []
    assert ler_historico(["12", "02/02/2026", "12"]) == []  


class ServidorFalso:

    def __init__(self):
        self.respostas = {"2": [b"3|#\n"], "4": [b"5|#\n"]}
        self.recebidos = []
        self._escuta = socket.socket()
        self._escuta.bind(("127.0.0.1", 0))
        self._escuta.listen(1)
        self.porta = self._escuta.getsockname()[1]
        threading.Thread(target=self._atender, daemon=True).start()

    def _atender(self):
        conexao, _ = self._escuta.accept()
        arquivo = conexao.makefile("rb")
        try:
            while True:
                quadro = ler(arquivo)
                self.recebidos.append(quadro)
                resposta = self.respostas.get(quadro[0], [])
                if resposta == "fechar":
                    return
                if resposta == "silencio":
                    continue
                for bruto in resposta:
                    conexao.sendall(bruto)
        except (EOFError, OSError):
            pass
        finally:
            conexao.close()

    def fechar(self):
        self._escuta.close()


@pytest.fixture
def servidor():
    s = ServidorFalso()
    yield s
    s.fechar()


def conectar(servidor, timeout=2, notificar=None):
    return Conexao("127.0.0.1", servidor.porta, timeout=timeout, notificar=notificar)


def test_conectar_envia_2_e_espera_3(servidor):
    conexao = conectar(servidor)
    assert servidor.recebidos == [["2"]]
    conexao.fechar()


def test_servidor_fora_do_ar():
    with pytest.raises(OSError):
        Conexao("127.0.0.1", 1, timeout=1) 


def test_pedir_devolve_campos_sem_o_codigo(servidor):
    servidor.respostas["16"] = [b"17|23|#\n"]
    conexao = conectar(servidor)
    assert conexao.pedir(AUTENTICAR, "fuciclano", "abc", esperado=AUTENTICADO) == ["23"]
    assert servidor.recebidos[-1] == ["16", "fuciclano", "abc"]


def test_quadro_nao_pedido_vai_para_o_tratador(servidor):
    servidor.respostas["16"] = [b"257|7|#\n", b"259|9|FALSO|#\n", b"17|1|#\n"]
    notificados = []
    conexao = conectar(servidor, notificar=notificados.append)
    assert conexao.pedir(AUTENTICAR, "ana", "x", esperado=AUTENTICADO) == ["1"]
    assert notificados == [["257", "7"], ["259", "9", "FALSO"]]


def test_erro_do_servidor(servidor):
    servidor.respostas["16"] = [b"32768|ERROAUTENTICACAO|Senha inv\xc3\xa1lida|#\n"]
    conexao = conectar(servidor)
    with pytest.raises(ErroServidor) as erro:
        conexao.pedir(AUTENTICAR, "ana", "x", esperado=AUTENTICADO)
    assert erro.value.categoria == "ERROAUTENTICACAO"
    assert erro.value.mensagem == "Senha inválida"


def test_categoria_numerica_e_mostrada_como_veio(servidor):
    servidor.respostas["16"] = [b"32768|2|#\n"]
    conexao = conectar(servidor)
    with pytest.raises(ErroServidor) as erro:
        conexao.pedir(AUTENTICAR, "ana", "x", esperado=AUTENTICADO)
    assert (erro.value.categoria, erro.value.mensagem) == ("2", "")


def test_servidor_fecha_a_conexao(servidor):
    servidor.respostas["4"] = "fechar"
    conexao = conectar(servidor)
    with pytest.raises(ConexaoPerdida):
        conexao.pedir(PING, esperado=PONG)
    with pytest.raises(ConexaoPerdida):  
        conexao.pedir(PING, esperado=PONG)


def test_servidor_nao_responde(servidor):
    servidor.respostas["4"] = "silencio"
    conexao = conectar(servidor, timeout=0.3)
    with pytest.raises(ConexaoPerdida):
        conexao.pedir(PING, esperado=PONG)


def test_enviar_sem_resposta_sucesso(servidor):
    conexao = conectar(servidor)
    conexao.enviar_sem_resposta(NOVAAMIZADE, "1", "2")
    assert servidor.recebidos[-2:] == [["256", "1", "2"], ["4"]]


def test_enviar_sem_resposta_com_erro(servidor):
    servidor.respostas["256"] = [b"32768|ERROCONEXAO|usuario nao existe|#\n"]
    conexao = conectar(servidor)
    with pytest.raises(ErroServidor) as erro:
        conexao.enviar_sem_resposta(NOVAAMIZADE, "1", "99")
    assert erro.value.categoria == "ERROCONEXAO"


def test_enviar_sem_resposta_ignora_confirmacao_inventada(servidor):
    servidor.respostas["256"] = [b"260|#\n"]  
    notificados = []
    conexao = conectar(servidor, notificar=notificados.append)
    conexao.enviar_sem_resposta(NOVAAMIZADE, "1", "2")
    assert notificados == [["260"]]


def test_pedir_de_varias_threads_nao_embaralha(servidor):
    servidor.respostas["4"] = [b"5|#\n"]
    conexao = conectar(servidor)
    erros = []

    def pinga():
        try:
            for _ in range(20):
                assert conexao.pedir(PING, esperado=PONG) == []
        except Exception as erro:
            erros.append(erro)

    threads = [threading.Thread(target=pinga) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert erros == []
    assert servidor.recebidos.count(["4"]) == 100
