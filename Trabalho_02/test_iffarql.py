import os
import tempfile

from src.arvore import Arvore
from src.banco import Banco
from src.comandos import interpretar
from src.erros import ErroIffarql
from src.lexer import tokenizar
from src.tipos import Data, Decimal, Inteiro, Texto, obter_tipo

SCRIPT = "iffarql_revenda_carros.txt"

def erro(fn, *args):
    """Verdadeiro se a chamada levantar ErroIffarql."""
    try:
        fn(*args)
    except ErroIffarql:
        return True
    return False

def test_lexer_mantem_frase_entre_aspas():
    """lexer mantem frase entre aspas como um token so"""
    assert tokenizar('INSERIREM cliente VALOR ("Joao da Silva" 20)') == [
        "INSERIREM", "cliente", "VALOR", "(", '"Joao da Silva"', "20", ")",
    ]

def test_lexer_ignora_espaco_extra():
    """lexer ignora espaco extra entre os tokens"""
    assert tokenizar("  MOSTRADADOSDE   carro  ") == ["MOSTRADADOSDE", "carro"]

def test_inteiro_converte_e_recusa_lixo():
    """INTEIRO converte digitos e recusa texto ou decimal"""
    assert Inteiro().converter("20") == 20
    assert erro(Inteiro().converter, "vinte")
    assert erro(Inteiro().converter, "1.5")

def test_decimal_aceita_inteiro_escrito():
    """DECIMAL aceita valor escrito sem casa decimal"""
    assert Decimal().converter("54990.00") == 54990.0
    assert Decimal().converter("20") == 20.0

def test_texto_remove_acento_e_aspas():
    """TEXTO tira as aspas e troca acento pelo caractere simples"""
    assert Texto().converter('"Adão"') == "Adao"

def test_data_valida_limites_do_enunciado():
    """DATA recusa dia fora do mes, sem bissexto"""
    assert erro(Data().converter, '"31/04/2020"')
    assert erro(Data().converter, '"00/01/2020"')
    assert Data().converter('"10/01/2026"') == (10, 1, 2026)

def test_data_soma_dias():
    """DATA soma INTEIRO de dias e chega numa data valida"""
    d = Data()
    assert d.formatar(d.operar(d.converter('"01/02/2023"'), "+", 123)) == "04/06/2023"

def test_operador_invalido_para_o_tipo():
    """cada tipo aceita so os operadores da sua linha na tabela"""
    booleano = obter_tipo("BOOLEANO")
    assert erro(booleano.operar, True, "+", True)
    assert erro(booleano.comparar, True, "<", False)
    assert booleano.comparar(True, "==", True) is True
    assert erro(Texto().operar, "a", "*", "b")

def test_arvore_insere_busca_remove():
    """arvore insere, busca por id e remove"""
    a = Arvore()
    for i in (5, 2, 8, 1):
        a.inserir(i, {"id": i})
    assert a.buscar(8) == {"id": 8}
    assert a.buscar(99) is None
    assert a.remover(2) is True
    assert a.buscar(2) is None

def test_arvore_percorre_em_ordem_de_id():
    """arvore percorre em ordem crescente de id"""
    a = Arvore()
    for i in (3, 1, 2):
        a.inserir(i, {"id": i})
    assert [r["id"] for r in a.percorrer()] == [1, 2, 3]

def test_arvore_de_lista_fica_balanceada():
    """arvore remontada do arquivo fica balanceada, nao vira lista"""
    a = Arvore.de_lista([{"id": i} for i in range(1, 8)])
    assert a.raiz.chave == 4

def banco_com_script():
    bd = Banco()
    interpretar(f"CARREGARIFFARQL {SCRIPT}").executar(bd)
    return bd

def test_carrega_script_de_exemplo():
    """CARREGARIFFARQL executa o script de exemplo inteiro"""
    bd = banco_com_script()
    assert set(bd.tabelas) == {"cliente", "vendedor", "carro", "caixa"}
    assert len(bd.obter("carro").selecionar(None)) == 8
    assert len(bd.obter("caixa").selecionar(None)) == 4

def test_id_automatico_comeca_em_um():
    """id e automatico e comeca em 1"""
    bd = banco_com_script()
    assert bd.obter("cliente").selecionar(None)[0]["id"] == 1
    assert bd.obter("cliente").proximo_id == 5

def test_onde_filtra():
    """ONDE filtra os registros da consulta"""
    bd = banco_com_script()
    saida = interpretar("MOSTRADADOSDE carro ONDE ano >= 2020").executar(bd)
    assert "Corolla" in saida and "Onix" not in saida

def test_com_usa_a_propria_coluna():
    """COM calcula o novo valor a partir da propria coluna"""
    bd = banco_com_script()
    precos = {c["modelo"]: c["preco"] for c in bd.obter("carro").selecionar(None)}
    assert precos["Corolla"] == 123990.00
    assert precos["Onix"] == 54990.00

def test_nao_apaga_registro_referenciado():
    """nao apaga registro nem tabela que outra tabela referencia"""
    bd = banco_com_script()
    assert erro(interpretar("APAGADADOSDE carro ONDE id == 1").executar, bd)
    assert erro(interpretar("APAGATABELA carro").executar, bd)

def test_fk_precisa_existir():
    """CHAVESTRANGEIRA so aceita id que existe na tabela referenciada"""
    bd = banco_com_script()
    assert erro(
        interpretar('INSERIREM caixa VALOR (999 1 1 10.0 "01/01/2026")').executar, bd
    )

def test_usuario_nao_cria_coluna_id():
    """usuario nao pode declarar uma coluna chamada id"""
    bd = Banco()
    assert erro(interpretar("CRIATABELA t ( id TEXTO )").executar, bd)

def test_carregariffarql_e_atomico():
    """erro no meio do CARREGARIFFARQL reverte o bloco inteiro"""
    bd = Banco()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("CRIATABELA t ( nome TEXTO )\nINSERIREM t VALOR (naoexiste)\n")
        caminho = f.name
    assert erro(interpretar(f"CARREGARIFFARQL {caminho}").executar, bd)
    os.unlink(caminho)


def test_salvar_e_carregar_preserva_proximo_id():
    """SALVARBD/CARREGARBD preservam o proximo id"""
    bd = banco_com_script()
    interpretar("APAGADADOSDE cliente ONDE id == 4").executar(bd)
    caminho = os.path.join(tempfile.gettempdir(), "bd_teste.json")
    interpretar(f"SALVARBD {caminho}").executar(bd)

    novo = Banco()
    interpretar(f"CARREGARBD {caminho}").executar(novo)
    assert len(novo.obter("cliente").selecionar(None)) == 3
    os.unlink(caminho)

