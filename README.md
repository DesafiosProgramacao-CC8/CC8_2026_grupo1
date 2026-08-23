### Alunos:
- Cauã Felipe Ziotti Tamiozzo
- Diego Breskovit Morcelli
- Talita Vargas de Souza 

## Estruturas de dados utilizadas

Para a indexação e busca dos arquivos, foi implementada uma Trie (árvore de prefixos), desenvolvida integralmente pelo grupo, sem uso de bibliotecas prontas de estrutura de dados. Cada nó da Trie (NoTrie) representa um caractere e mantém um dicionário de filhos, uma flag indicando se aquele nó corresponde ao fim de uma palavra válida e, quando é o caso, um dicionário associando cada arquivo à quantidade de vezes que a palavra ocorre nele. Essa escolha foi motivada por três fatores:

- Busca por prefixo eficiente: como o sistema precisa oferecer uma experiência de pesquisa nos moldes de um buscador (similar ao Google), a Trie permite localizar todas as palavras que começam com um determinado termo percorrendo apenas os caracteres do prefixo buscado, sem precisar varrer toda a base de palavras indexadas diferente do que ocorreria com uma lista ou uma tabela hash simples.

-Compartilhamento de prefixos comuns: palavras com prefixos iguais (ex.: "relatorio" e "relacionamento") compartilham o mesmo caminho inicial na árvore, reduzindo redundância de armazenamento em relação a estruturas que tratam cada palavra de forma independente.

-Base natural para o cálculo de relevância: por armazenar, em cada nó de fim de palavra, a frequência de ocorrência por arquivo, a Trie já fornece diretamente o dado necessário para o cálculo de relevância dos documentos (frequência do termo buscado no conteúdo de cada arquivo), exigido pelo trabalho.

Como o sistema precisa manter índices separados para imagens e documentos, foi criada a classe IndicesArquivos, que encapsula duas instâncias independentes da Trie — uma para o índice de imagens e outra para o índice de documentos — expondo um método (arvore_para_tipo) que resolve qual árvore deve ser utilizada de acordo com o tipo de arquivo pesquisado.

## To-do list

### Feito
- [x] Seleção da pasta pelo usuário e varredura recursiva de subpastas (`core/scanner.py` + `core/indexer.py`)
- [x] Identificação/classificação dos arquivos por extensão (`core/scanner.py::classificar_arquivo`, extensões em `core/config.py`)
- [x] Armazenamento das informações de cada arquivo (nome, caminho, tipo, tamanho, metadados)
- [x] Estrutura de dados do tipo Árvore implementada pelo grupo: Trie com `inserir`, `buscar`, `buscar_prefixo` e coleta por DFS (`core/trees/trie.py`) — os três métodos são usados pela busca
- [x] Índices separados para imagens e documentos (`IndicesArquivos`, `core/trees/__init__.py`)
- [x] Extração de metadados de imagem com Pillow (`core/extractors/image_extractor.py`) — *obs.: a tela mostra só largura/altura/formato; `modo_cor` e `modificado_em` são extraídos e nunca usados*
- [x] Extração do conteúdo textual de .txt, com limite de leitura (`core/extractors/text_extractor.py`)
- [x] Contagem das palavras mais comuns de cada documento, com stopwords (`core/relevance.py`)
- [x] Indexação do nome do arquivo (tokenizado) e do conteúdo dos documentos na Trie
- [x] Pesquisa por nome e filtro por tipo (tudo / imagens / documentos) (`core/search.py`)
- [x] Cálculo de relevância (soma das frequências dos termos) e ordenação dos resultados
- [x] Interface Web em Flask: home, indexar, resultados (`app.py`, `templates/`)
- [x] Visualizar/abrir os arquivos encontrados (rota `/arquivo`, com bloqueio de acesso fora da pasta indexada)
- [x] Persistência do índice em disco para não reindexar a cada reinício (`storage/persistence.py`)
- [x] Varredura feita pelo `core/scanner.py`, que ignora arquivos/pastas sem permissão de leitura e continua a indexação (requisito da "Observação final" do edital)
- [x] Palavras mais comuns de cada documento guardadas em `metadados["palavras_comuns"]` e exibidas na página de resultados (`core/relevance.py::palavras_mais_comuns`)
- [x] Relevância combina busca por prefixo e busca exata na Trie: quem escreve a palavra inteira ganha peso extra (`Trie.buscar` + `BONUS_PALAVRA_EXATA` em `core/search.py`)
- [x] Aba "Imagens" exibe os resultados em grade justificada (estilo Google Imagens), usando `largura`/`altura` dos metadados para a proporção de cada miniatura, com visualizador ampliado ao clicar (`templates/resultados.html`)

> Os stubs `core/trees/base_index.py`, `core/trees/content_index.py`, `core/trees/file_name_index.py` e `core/models.py` foram removidos: nunca chegaram a ser implementados e a `Trie` (`core/trees/trie.py`) é a estrutura oficial do projeto.

### Pendentes
- [ ] Pesquisar imagens por metadados (largura, altura, formato); hoje imagens só são encontradas pelo nome
- [ ] Contador `total_arquivos` conta também os arquivos ignorados (soma não bate com imagens + documentos)
- [ ] Relatório/documentação de todas as partes
