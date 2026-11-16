OFFSET = 0x811C9DC5      # valor inicial do FNV de 32 bits
PRIMO = 0x01000193       # primo do FNV de 32 bits
MASCARA = 0xFFFFFFFF     # mantém o resultado em 32 bits

def fnv1a(senha: str) -> str:
    h = OFFSET
    for byte in senha.encode("utf-8"):
        h ^= byte 
        h = (h * PRIMO) & MASCARA
    return f"{h:08x}"

def passos(senha: str) -> list[tuple[int, str, str]]:
    tabela = []
    h = OFFSET
    for byte in senha.encode("utf-8"):
        h ^= byte
        depois_xor = f"{h:08x}"
        h = (h * PRIMO) & MASCARA
        tabela.append((byte, depois_xor, f"{h:08x}"))
    return tabela

def senha_valida(senha: str) -> bool:
    return len(senha) == 6 and senha.isascii() and senha.isalnum()

VETORES = {"": "811c9dc5", "a": "e40c292c", "foobar": "bf9cf968"}

if __name__ == "__main__":
    for entrada, esperado in VETORES.items():
        assert fnv1a(entrada) == esperado, (entrada, fnv1a(entrada), esperado)
    print("auto-checagem ok:", ", ".join(f"{e!r} -> {s}" for e, s in VETORES.items()))

    exemplo = "abc123"
    print(f"\nexemplo {exemplo!r} -> {fnv1a(exemplo)}")
    print(f"{'byte':>4} {'char':>4} {'após XOR':>10} {'após * primo':>12}")
    for byte, xor, mult in passos(exemplo):
        print(f"{byte:>4} {chr(byte):>4} {xor:>10} {mult:>12}")
