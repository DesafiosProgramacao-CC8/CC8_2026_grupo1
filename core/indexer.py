import os
import re
from core.trees import IndicesArquivos
from core.config import EXTENSOES_IMAGEM, EXTENSOES_DOCUMENTO
from core.extractors import extrair_metadados_imagem, extrair_dados_documento

def tokenizar(texto): #deixa tudo mínusculo para facilitar a busca
    return re.findall(r"\w+", texto.lower())

class Indexador:
    def __init__(self):
        self.pasta_indexada = None

        self.total_arquivos = 0
        self.total_imagens = 0
        self.total_documentos = 0
        self.total_ignorados = 0

        self.indices = IndicesArquivos()

        self.registro_arquivos = {}


    def indexar_pasta(self, pasta):
        self.pasta_indexada = os.path.abspath(pasta)

        for pasta_atual, subpastas, arquivos in os.walk(self.pasta_indexada):
            for nome_arquivo in arquivos:
                caminho = os.path.join(pasta_atual, nome_arquivo)
                extensao = os.path.splitext(nome_arquivo)[1].lower()

                self.total_arquivos += 1

                if extensao in EXTENSOES_IMAGEM:
                    tipo = "imagem"
                elif extensao in EXTENSOES_DOCUMENTO:
                    tipo = "documento"
                else:
                    self.total_ignorados += 1
                    continue

                try:
                    arvore = self.indices.arvore_para_tipo(tipo)

                    for palavra in tokenizar(nome_arquivo):
                        arvore.inserir(palavra, caminho)

                    if tipo == "imagem":
                        metadados = extrair_metadados_imagem(caminho)
                    else:
                        dados = extrair_dados_documento(caminho)
                        metadados = {"trecho": dados["trecho"]}

                        for palavra, frequencia in dados["palavras"].items():
                            for _ in range(frequencia):
                                arvore.inserir(palavra, caminho)

                    self.registro_arquivos[caminho] = {
                        "nome": nome_arquivo,
                        "caminho": caminho,
                        "tipo": tipo,
                        "tamanho_bytes": os.path.getsize(caminho),
                        "metadados": metadados
                    }

                    if tipo == "imagem":
                        self.total_imagens += 1
                    else:
                        self.total_documentos += 1

                except Exception as e:
                    self.total_ignorados += 1