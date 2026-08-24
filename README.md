### Alunos:

- Cauã Felipe Ziotti Tamiozzo
- Diego Breskovit Morcelli
- Talita Vargas de Souza

## Estruturas de dados utilizadas

Para a indexação e busca dos arquivos, foi implementada uma Trie (árvore de prefixos), desenvolvida integralmente pelo grupo, sem uso de bibliotecas prontas de estrutura de dados. Cada nó da Trie (NoTrie) representa um caractere e mantém um dicionário de filhos, uma flag indicando se aquele nó corresponde ao fim de uma palavra válida e, quando é o caso, um dicionário associando cada arquivo à quantidade de vezes que a palavra ocorre nele. Essa escolha foi motivada por três fatores:

- Busca por prefixo eficiente: como o sistema precisa oferecer uma experiência de pesquisa nos moldes de um buscador (similar ao Google), a Trie permite localizar todas as palavras que começam com um determinado termo percorrendo apenas os caracteres do prefixo buscado, sem precisar varrer toda a base de palavras indexadas diferente do que ocorreria com uma lista ou uma tabela hash simples.

- Compartilhamento de prefixos comuns: palavras com prefixos iguais (ex.: "relatorio" e "relacionamento") compartilham o mesmo caminho inicial na árvore, reduzindo redundância de armazenamento em relação a estruturas que tratam cada palavra de forma independente.

- Base natural para o cálculo de relevância: por armazenar, em cada nó de fim de palavra, a frequência de ocorrência por arquivo, a Trie já fornece diretamente o dado necessário para o cálculo de relevância dos documentos (frequência do termo buscado no conteúdo de cada arquivo), exigido pelo trabalho.

Como o sistema precisa manter índices separados para imagens e documentos, foi criada a classe IndicesArquivos, que encapsula duas instâncias independentes da Trie — uma para o índice de imagens e outra para o índice de documentos — expondo um método (arvore_para_tipo) que resolve qual árvore deve ser utilizada de acordo com o tipo de arquivo pesquisado.

## Guia de uso dos filtros de metadados

Vale para a busca de **imagens** (aba "Imagens" ou "Tudo"). A consulta aceita
dois formatos, que podem ser misturados:

- **Filtro por campo** — `campo:valor`, ex.: `tipo:png`.
- **Termo livre** — palavra solta, ex.: `paisagem`, `1920x1080`, `colorida`.

Vários termos funcionam como **E**: o arquivo precisa casar com todos eles.
O `+` vale como separador, igual ao espaço.

```
praia tipo:jpg                    imagem jpg com "praia" no nome
tipo:jpg+orientacao:horizontal    jpg na horizontal
tipo:jpg orientacao:vertical      sem resultados se nenhuma jpg for vertical
1920x1080 colorida                por dimensão exata e por cor
```

> Códigos usados na busca por metadados

| Campo        | Valores                              | Descrição                                          |
| :----------- | :----------------------------------- | :------------------------------------------------- |
| `tipo`       | `jpg`, `jpeg`, `png`                 | Formato do arquivo                                 |
| `orientacao` | `horizontal`, `vertical`, `quadrada` | Largura vs. altura                                 |
| `cor`        | `colorida`, `pb`                     | Tem cor ou é tons de cinza                         |
| `tamanho`    | `grande`, `media`, `pequena`         | Resolução: ≥ 1920px / entre / ≤ 400px (maior lado) |
| `peso`       | `leve`, `moderada`, `pesada`         | Arquivo: < 100 KB / entre / > 2 MB                 |
| `ano`        | `2024`, `2025`, ...                  | Ano da última modificação                          |

> Termos de busca por metadados em busca livre

| Metadado   | Termos aceitos                                                               |
| :--------- | :--------------------------------------------------------------------------- |
| Formato    | `jpeg`, `png`                                                                |
| Dimensões  | `1920x1080`, ou só a largura (`1920`) ou a altura (`1080`)                   |
| Orientação | `paisagem`/`horizontal`, `retrato`/`vertical`, `quadrada`                    |
| Resolução  | `grande` (≥ 1920px), `media`, `pequena` (≤ 400px)                            |
| Cor        | `colorida`/`cor`/`color`, ou `pb`/`preta`/`branca`/`cinza`/`bw`/`grayscale`; |
| Peso       | `leve` (< 100 KB), `moderada`, `pesada` (> 2 MB)                             |
| Ano        | `2024`, `2025`, ...                                                          |

Os filtros por campo (`tipo:`, `orientacao:`, …) são os mais previsíveis, porque
cada valor é único. Os termos livres são mais soltos: casam por prefixo e
convivem com as palavras do nome do arquivo.

## To-do list

### Feito

- [x] Seleção da pasta pelo usuário e varredura recursiva de subpastas
- [x] Identificação dos arquivos por extensão
- [x] Armazenamento das informações de cada arquivo (nome, caminho, tipo, tamanho, metadados)
- [x] Estrutura de dados do tipo Árvore implementada pelo grupo: Trie
- [x] Índices separados para imagens e documentos
- [x] Extração de metadados de imagem com Pillow
- [x] Extração do conteúdo textual de .txt
- [x] Contagem das palavras mais comuns de cada documento
- [x] Indexação do nome do arquivo (tokenizado) e do conteúdo dos documentos na Trie
- [x] Pesquisa por nome e filtro por tipo (tudo / imagens / documentos)
- [x] Cálculo de relevância e ordenação dos resultados
- [x] Interface Web em Flask: home, indexar, resultados
- [x] Visualizar/abrir os arquivos encontrados
- [x] Persistência do índice em disco
- [x] Varredura que ignora arquivos e diretórios sem permissão de leitura e continua a indexação
- [x] Relevância combina busca por prefixo e busca exata na Trie
- [x] Aba "Imagens" exibe os resultados em grade
- [x] Pesquisar imagens por metadados (largura, altura, formato)
- [x] Contador conta também os arquivos ignorados

### Pendentes

- [ ] Relatório/documentação de todas as partes
