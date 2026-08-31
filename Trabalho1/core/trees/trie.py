class NoTrie: #classe para fazer a criação do nó da árvore trie
    def __init__(self):
        self.filhos = {}

        self.fim_palavra = False

        self.ocorrencia = {}


class Trie: #classe para fazer a criação da árvore trie
    def __init__(self):
        self.raiz = NoTrie()

    '''
    valida se o caractere da palavra já existe no nó atual,
    caso não exista, cria um novo nó e adiciona ao dicionário de 
    filhos do nó atual.
    '''
    def inserir(self, palavra, arquivo): 
        no_atual = self.raiz

        for caractere in palavra:
            if caractere not in no_atual.filhos:
                no_atual.filhos[caractere] = NoTrie()

            no_atual = no_atual.filhos[caractere]

        no_atual.fim_palavra = True

        no_atual.ocorrencia[arquivo] = no_atual.ocorrencia.get(arquivo, 0) + 1

    '''
    faz a busca de palavra na árvore, se a palavra existe,
    retorna um dicionário com os arquivos e a quantidade de 
    ocorrências da palavra em cada arquivo, caso contrário,
    retorna um dicionário vazio. ->padronizado retorno {}
    e não None, NÃO alterar <-
    '''
    def buscar(self, palavra):
        no_atual = self.raiz

        for caractere in palavra:
            if caractere not in no_atual.filhos:
                return {}

            no_atual = no_atual.filhos[caractere]

        if not no_atual.fim_palavra:
            return {}

        return no_atual.ocorrencia

    '''
    faz a busca de prefixo na árvore, se o prefixo existe,
    retorna um dicionário com os arquivos e a quantidade de
    ocorrências de todas as palavras que começam com o prefixo em cada arquivo,
    caso contrário, retorna um dicionário vazio. Cuidar retorno também
    '''
    def buscar_prefixo(self, prefixo):
        no_atual = self.raiz

        for caractere in prefixo:
            if caractere not in no_atual.filhos:
                return {}
            no_atual = no_atual.filhos[caractere]

        resultados = {}

        self.coletar_ocorrencias(no_atual, resultados)

        return resultados

    '''
    aqui implementamos uma recursão para percorrer todo os nós da árvore
    e coletar as ocorrências de todas as palavras que começam com o prefixo.
    Temos uma DFS busca em profundidade aplicada.
    '''
    def coletar_ocorrencias(self, no, resultados):
        if no.fim_palavra:

            for arquivo, ocorrencia in no.ocorrencia.items():
                resultados[arquivo] = resultados.get(arquivo, 0) + ocorrencia

        for filho in no.filhos.values():
            self.coletar_ocorrencias(filho, resultados)


#teste de inserção e busca na árvore trie
# if __name__ == "__main__":
#     t = Trie()
#     t.inserir("relatorio", "notas.txt")
#     t.inserir("relatorio", "notas.txt")
#     t.inserir("relacionamento", "outro.txt")

#     print(t.buscar("relatorio"))
#     print(t.buscar("rela"))
#     print(t.buscar_prefixo("rela"))

'''
CONTRATO
indices = IndicesArquivos()
indices.arvore_para_tipo("documento").inserir("relatorio", "/caminho/notas.txt")
indices.arvore_para_tipo("documento").buscar_prefixo("rela")
'''