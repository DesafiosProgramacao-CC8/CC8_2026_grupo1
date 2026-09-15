import os
import re
from core.trees import IndicesArquivos
from core.scanner import varrer_pasta, classificar_arquivo
from core.extractors import (
    extrair_metadados_imagem,
    extrair_dados_documento,
    gerar_termos_busca_imagem,
    gerar_termos_por_campo_imagem,
)
from core.relevance import palavras_mais_comuns

TOP_PALAVRAS_DOCUMENTO = 10

def tokenizar(texto):
    return re.findall(r"[^\W_]+", texto.lower())

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

        for caminho in varrer_pasta(self.pasta_indexada):
            nome_arquivo = os.path.basename(caminho)

            self.total_arquivos += 1

            tipo = classificar_arquivo(caminho)

            if tipo is None:
                self.total_ignorados += 1
                continue

            try:
                arvore = self.indices.arvore_para_tipo(tipo)

                for palavra in tokenizar(nome_arquivo):
                    arvore.inserir(palavra, caminho)

                if tipo == "imagem":
                    metadados = extrair_metadados_imagem(caminho)

                    for termo in gerar_termos_busca_imagem(metadados):
                        arvore.inserir(termo, caminho)

                    for campo, valor in gerar_termos_por_campo_imagem(metadados):
                        arvore.inserir(f"{campo}:{valor}", caminho)
                else:
                    dados = extrair_dados_documento(caminho)
                    metadados = {
                        "trecho": dados["trecho"],
                        "palavras_comuns": palavras_mais_comuns(
                            dados["palavras"], TOP_PALAVRAS_DOCUMENTO
                        ),
                    }

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
                print(f"[indexer] Aviso: nao foi possivel indexar '{caminho}': {e}")
                self.total_ignorados += 1