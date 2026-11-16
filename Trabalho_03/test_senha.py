import pytest

from senha import OFFSET, fnv1a, passos, senha_valida


@pytest.mark.parametrize("entrada, esperado", [
    ("", "811c9dc5"),
    ("a", "e40c292c"),
    ("foobar", "bf9cf968"),
])
def test_vetores_oficiais(entrada, esperado):
    assert fnv1a(entrada) == esperado


def test_saida_sempre_oito_hex_minusculos():
    for senha in ["abc123", "ZZZZZZ", "000000", "ação12", "x"]:
        saida = fnv1a(senha)
        assert len(saida) == 8
        assert saida == saida.lower()
        int(saida, 16) 


def test_senhas_diferentes_dao_hashes_diferentes():
    assert fnv1a("abc123") != fnv1a("abc124")


def test_passos_batem_com_o_hash():
    tabela = passos("abc123")
    assert len(tabela) == 6
    assert [b for b, _, _ in tabela] == list(b"abc123")
    assert tabela[-1][2] == fnv1a("abc123")
    assert passos("") == [] and fnv1a("") == f"{OFFSET:08x}"


@pytest.mark.parametrize("senha", ["abc123", "ABCDEF", "123456", "a1B2c3"])
def test_senha_valida(senha):
    assert senha_valida(senha)


@pytest.mark.parametrize("senha", ["abc12", "abc1234", "abc 12", "ação12", "abc-12", "", "abc12|"])
def test_senha_invalida(senha):
    assert not senha_valida(senha)
