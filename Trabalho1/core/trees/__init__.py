from core.trees.trie import Trie

class IndicesArquivos:
    def __init__(self):
        self.arvore_imagens = Trie()
        self.arvore_documentos = Trie()

    #vai decidir qual árvore será usada dependendo do tipo de arquivo
    def arvore_para_tipo(self, tipo):
        if tipo == "imagem":
            return self.arvore_imagens
        elif tipo == "documento":
            return self.arvore_documentos
        else:
            raise ValueError("Tipo inválido. Use 'imagem' ou 'documento'.")