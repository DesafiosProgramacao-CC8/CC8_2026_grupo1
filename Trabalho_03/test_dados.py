import threading
import time
from datetime import date, datetime
from dados import Contato, ErroChat, Mensagem, Perfil, RepositorioIffarql
import pytest

HOJE = date(2026, 11, 15)
SENHA = "a9f37ed7"     # formato do hash do cliente; para o banco é só texto


@pytest.fixture
def repo(tmp_path):
    r = RepositorioIffarql(tmp_path / "chat.json", hoje=lambda: HOJE)
    yield r
    r.fechar()


def test_cria_banco_com_as_tres_tabelas(repo, tmp_path):
    assert (tmp_path / "chat.json").exists()
    assert repo._executar(lambda bd: list(bd.tabelas)) == ["usuario", "amizade", "conversa"]


def test_reabre_banco_existente(tmp_path):
    caminho = tmp_path / "chat.json"
    primeiro = RepositorioIffarql(caminho)
    primeiro._executar(lambda bd: bd.inserir("usuario", ['"a"', '"a"', '"01/01/2000"', '"x"']))
    primeiro.fechar()

    segundo = RepositorioIffarql(caminho)
    total = segundo._executar(lambda bd: len(bd.selecionar("usuario", None)))
    segundo.fechar()
    assert total == 1 #registro sobreviveu ao reinício


def test_executa_na_thread_do_trabalhador(repo):
    nome = repo._executar(lambda bd: threading.current_thread().name)
    assert nome == "trabalhador-bd"


def test_excecao_chega_em_quem_pediu_e_desfaz(repo):
    def insere_e_falha(bd):
        bd.inserir("usuario", ['"a"', '"a"', '"01/01/2000"', '"x"'])
        raise ValueError("falhou no meio")

    with pytest.raises(ValueError):
        repo._executar(insere_e_falha)

    assert repo._executar(lambda bd: bd.selecionar("usuario", None)) == []   # rollback
    assert repo._executar(lambda bd: "vivo") == "vivo"                       # trabalhador não morreu


def test_fila_serializa_acessos_concorrentes(repo):
    contador = {"valor": 0}

    def incrementa(bd):
        lido = contador["valor"]
        time.sleep(0.001)            # abre espaço para outra thread "atropelar"
        contador["valor"] = lido + 1

    threads = [threading.Thread(target=repo._executar, args=(incrementa,)) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert contador["valor"] == 20


# usuário

def test_registrar_e_autenticar(repo):
    repo.registrar("Ana Souza", "ana", "10/05/2000", SENHA)
    repo.registrar("Beto Lima", "beto", "10/05/2000", SENHA)
    assert repo.autenticar("ana", SENHA) == 1
    assert repo.autenticar("beto", SENHA) == 2


def test_apelido_repetido(repo):
    repo.registrar("Ana", "ana", "10/05/2000", SENHA)
    with pytest.raises(ErroChat) as erro:
        repo.registrar("Outra Ana", "ana", "10/05/2000", SENHA)
    assert erro.value.categoria == "ERROREGISTRO"


@pytest.mark.parametrize("data", ["2000-05-10", "31/02/2000", "29/02/2000", "16/11/2026", "1/5/2000"])
def test_data_invalida(repo, data):
    with pytest.raises(ErroChat) as erro:
        repo.registrar("Ana", "ana", data, SENHA)
    assert erro.value.categoria == "ERROREGISTRO"


@pytest.mark.parametrize("apelido, senha", [("ana", "errada00"), ("ninguem", SENHA)])
def test_autenticacao_falha(repo, apelido, senha):
    repo.registrar("Ana", "ana", "10/05/2000", SENHA)
    with pytest.raises(ErroChat) as erro:
        repo.autenticar(apelido, senha)
    assert erro.value.categoria == "ERROAUTENTICACAO"


def test_texto_preserva_acentos_e_aspas(repo):
    nome = 'João "Zé" da Ação'
    repo.registrar(nome, "joão", "10/05/2000", SENHA)
    assert repo.perfil(1).nome == nome
    assert repo.perfil(1).apelido == "joão"
    assert repo.autenticar("joão", SENHA) == 1


@pytest.mark.parametrize("nascimento, idade", [("15/11/2000", 26), ("16/11/2000", 25)])
def test_idade(repo, nascimento, idade):
    repo.registrar("Ana", "ana", nascimento, SENHA)
    assert repo.perfil(1) == Perfil("Ana", "ana", idade)


def test_perfil_inexistente(repo):
    with pytest.raises(ErroChat) as erro:
        repo.perfil(99)
    assert erro.value.categoria == "ERROVERPERFIL"


def test_atualizar_perfil(repo):
    repo.registrar("Ana", "ana", "10/05/2000", SENHA)
    with pytest.raises(ErroChat) as erro:
        repo.atualizar_perfil(1, "Ana Nova", "10/05/1990", "errada00")
    assert erro.value.categoria == "ERROATUALIZARPERFIL"

    repo.atualizar_perfil(1, "Ana Nova", "10/05/1990", SENHA)
    assert repo.perfil(1) == Perfil("Ana Nova", "ana", 36)
    assert repo.autenticar("ana", SENHA) == 1      # a senha não mudou


# amizade

@pytest.fixture
def tres(repo):
    """Repositório com ana (1), beto (2) e caio (3) registrados."""
    for apelido in ["ana", "beto", "caio"]:
        repo.registrar(apelido.title(), apelido, "10/05/2000", SENHA)
    return repo


def amizade(repo, a, b):
    repo.pedir_amizade(a, b)
    repo.responder_amizade(b, a, True)


def linhas(repo):
    """Cópia das linhas de amizade, para inspecionar nos testes."""
    return repo._executar(lambda bd: [dict(l) for l in bd.selecionar("amizade", None)])


def test_pedido_cria_duas_linhas_pendentes(tres):
    tres.pedir_amizade(1, 2)
    assert [(x["id_usuario_1"], x["id_usuario_2"], x["aceita"], x["ha_notificacao"])
            for x in linhas(tres)] == [(1, 2, False, False), (2, 1, False, True)]


def test_pendente_so_para_o_alvo(tres):
    tres.pedir_amizade(1, 2)
    assert tres.pedidos_pendentes(2) == [1]
    assert tres.pedidos_pendentes(1) == []
    assert tres.amigos(1) == []        # pendente não é amigo
    assert tres.amigos(2) == []


@pytest.mark.parametrize("solicitante, alvo", [(1, 1), (1, 99)])
def test_pedido_invalido(tres, solicitante, alvo):
    with pytest.raises(ErroChat) as erro:
        tres.pedir_amizade(solicitante, alvo)
    assert erro.value.categoria == "ERROCONEXAO"


def test_pedido_duplicado_nos_dois_sentidos(tres):
    tres.pedir_amizade(1, 2)
    for a, b in [(1, 2), (2, 1)]:
        with pytest.raises(ErroChat) as erro:
            tres.pedir_amizade(a, b)
        assert erro.value.categoria == "ERROCONEXAO"


def test_aceitar(tres):
    amizade(tres, 1, 2)
    assert tres.amigos(1) == [Contato(2, "beto")]
    assert tres.amigos(2) == [Contato(1, "ana")]
    assert tres.pedidos_pendentes(2) == []


def test_recusar_apaga_as_duas_linhas(tres):
    tres.pedir_amizade(1, 2)
    tres.responder_amizade(2, 1, False)
    assert linhas(tres) == []
    tres.pedir_amizade(1, 2)           # pode pedir de novo


def test_solicitante_nao_aceita_o_proprio_pedido(tres):
    tres.pedir_amizade(1, 2)
    with pytest.raises(ErroChat) as erro:
        tres.responder_amizade(1, 2, True)
    assert erro.value.categoria == "ERROCONEXAO"


def test_responder_sem_pedido(tres):
    with pytest.raises(ErroChat):
        tres.responder_amizade(2, 1, True)
    amizade(tres, 1, 2)
    with pytest.raises(ErroChat):
        tres.responder_amizade(2, 1, True)   # já foi aceito


def test_silenciar_alterna_so_a_propria_linha(tres):
    amizade(tres, 1, 2)
    tres.alternar_silencio(1, 2)
    assert {(x["id_usuario_1"], x["bloqueado"]) for x in linhas(tres)} == {(1, True), (2, False)}
    tres.alternar_silencio(1, 2)
    assert all(not x["bloqueado"] for x in linhas(tres))


def test_silenciar_quem_nao_e_amigo(tres):
    tres.pedir_amizade(1, 2)
    for a, b in [(1, 2), (1, 3)]:      # pendente e sem relação nenhuma
        with pytest.raises(ErroChat) as erro:
            tres.alternar_silencio(a, b)
        assert erro.value.categoria == "ERROMENSAGENS"


def test_varios_amigos(tres):
    amizade(tres, 1, 2)
    amizade(tres, 3, 1)                # caio pediu para ana
    assert tres.amigos(1) == [Contato(2, "beto"), Contato(3, "caio")]

# mensagens privadas

QUANDO = datetime(2026, 11, 15, 9, 5)


@pytest.fixture
def amigos(tres):
    """ana (1) e beto (2) já são amigos; caio (3) não é amigo de ninguém."""
    amizade(tres, 1, 2)
    return tres


def test_enviar_e_historico_nos_dois_sentidos(amigos):
    amigos.enviar_privada(1, 2, "oi beto", QUANDO)
    amigos.enviar_privada(2, 1, "oi ana", QUANDO)
    amigos.enviar_privada(1, 2, "tudo bem?", QUANDO)
    esperado = [
        Mensagem(1, "oi beto", "15/11/2026", 9, 5),
        Mensagem(2, "oi ana", "15/11/2026", 9, 5),
        Mensagem(1, "tudo bem?", "15/11/2026", 9, 5),
    ]
    assert amigos.historico(1, 2) == esperado
    assert amigos.historico(2, 1) == esperado      # os dois veem a mesma conversa


def test_texto_preserva_acentos_aspas_e_barra(amigos):
    texto = 'Ação "x" | 100% ok? sim/não'
    amigos.enviar_privada(1, 2, texto, QUANDO)
    assert amigos.novas_privadas(2, 1)[0].texto == texto


@pytest.mark.parametrize("pedir", [False, True])
def test_enviar_sem_amizade_aceita(tres, pedir):
    if pedir:
        tres.pedir_amizade(1, 2)                   # pendente também não vale
    with pytest.raises(ErroChat) as erro:
        tres.enviar_privada(1, 2, "oi", QUANDO)
    assert erro.value.categoria == "ERROENVIARMENSAGEM"


def test_notificacao_so_para_o_destinatario(amigos):
    amigos.enviar_privada(1, 2, "oi", QUANDO)
    assert amigos.notificacoes(2) == [1]
    assert amigos.notificacoes(1) == []


def test_pedido_pendente_nao_e_notificacao_de_mensagem(tres):
    tres.pedir_amizade(1, 2)
    assert tres.notificacoes(2) == []


def test_novas_entrega_uma_vez_e_limpa_notificacao(amigos):
    amigos.enviar_privada(1, 2, "um", QUANDO)
    amigos.enviar_privada(1, 2, "dois", QUANDO)
    assert [m.texto for m in amigos.novas_privadas(2, 1)] == ["um", "dois"]
    assert amigos.notificacoes(2) == []
    assert amigos.novas_privadas(2, 1) == []       # segunda chamada: nada novo
    amigos.enviar_privada(1, 2, "tres", QUANDO)
    assert [m.texto for m in amigos.novas_privadas(2, 1)] == ["tres"]


def test_novas_nao_devolve_as_proprias(amigos):
    amigos.enviar_privada(1, 2, "minha", QUANDO)
    assert amigos.novas_privadas(1, 2) == []


def test_historico_marca_como_lidas(amigos):
    amigos.enviar_privada(1, 2, "oi", QUANDO)
    amigos.historico(2, 1)
    assert amigos.notificacoes(2) == []
    assert amigos.novas_privadas(2, 1) == []


def test_silenciado_some_da_notificacao_mas_mensagem_chega(amigos):
    amigos.alternar_silencio(2, 1)                 # beto silencia ana
    amigos.enviar_privada(1, 2, "oi", QUANDO)
    assert amigos.notificacoes(2) == []
    assert [m.texto for m in amigos.novas_privadas(2, 1)] == ["oi"]


def test_conversas_separadas_por_amigo(amigos):
    amizade(amigos, 3, 1)
    amigos.enviar_privada(2, 1, "do beto", QUANDO)
    amigos.enviar_privada(3, 1, "do caio", QUANDO)
    assert sorted(amigos.notificacoes(1)) == [2, 3]
    assert [m.texto for m in amigos.novas_privadas(1, 2)] == ["do beto"]
    assert amigos.notificacoes(1) == [3]           # ler o beto não limpa o caio
    assert [m.texto for m in amigos.historico(1, 3)] == ["do caio"]


@pytest.mark.parametrize("metodo, categoria", [
    ("novas_privadas", "ERROMENSAGENS"),
    ("historico", "ERROHISTORICOMENSAGENS"),
])
def test_ler_sem_amizade(tres, metodo, categoria):
    with pytest.raises(ErroChat) as erro:
        getattr(tres, metodo)(1, 2)
    assert erro.value.categoria == categoria


def test_historico_sobrevive_ao_reinicio(tmp_path):
    caminho = tmp_path / "chat.json"
    r = RepositorioIffarql(caminho, hoje=lambda: HOJE)
    r.registrar("Ana", "ana", "10/05/2000", SENHA)
    r.registrar("Beto", "beto", "10/05/2000", SENHA)
    amizade(r, 1, 2)
    r.enviar_privada(1, 2, "oi", QUANDO)
    antes = r.historico(1, 2)
    r.fechar()
    r = RepositorioIffarql(caminho, hoje=lambda: HOJE)
    assert r.historico(1, 2) == antes
    r.fechar()


# desempenho

@pytest.mark.parametrize("consulta", [
    lambda r: r.autenticar("ana", SENHA),
    lambda r: r.perfil(1),
    lambda r: r.amigos(1),
    lambda r: r.pedidos_pendentes(1),
    lambda r: r.notificacoes(1),
], ids=["autenticar", "perfil", "amigos", "pedidos_pendentes", "notificacoes"])
def test_consulta_nao_regrava_o_arquivo(repo, tmp_path, consulta):
    repo.registrar("Ana", "ana", "10/05/2000", SENHA)
    arquivo = tmp_path / "chat.json"
    arquivo.unlink()                       # apaga o arquivo salvo

    consulta(repo)
    assert not arquivo.exists()            # leitura não salvou

    repo.registrar("Beto", "beto", "10/05/2000", SENHA)
    assert arquivo.exists()                # escrita continua salvando
