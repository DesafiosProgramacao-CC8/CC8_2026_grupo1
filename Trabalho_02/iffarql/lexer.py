import re
from iffarql.erros import ErroIffarql

_TOKEN = re.compile(r'"[^"]*"|[()]|[^\s()]+')

def tokenizar(linha: str) -> list[str]:
    # Exemplo: VALOR ("Joao" true) -> ['VALOR', '(', '"Joao"', 'true', ')']
    if linha.count('"') % 2:
        raise ErroIffarql(f"aspas nao fechadas em: {linha.strip()}")
    return _TOKEN.findall(linha)
