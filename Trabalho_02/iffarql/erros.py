class ErroIffarql(Exception):
    # Erro de execução do IFFARQL: tipagem inválida, comando malformado,
    # violaçao de regra de negocio (FK, tabela inexistente, etc...)