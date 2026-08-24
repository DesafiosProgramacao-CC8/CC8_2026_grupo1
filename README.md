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

| Campo | Valores Possíveis | O Que Representa |
| :--- | :---: | :--- |
| `tipo` | `jpg`, `jpeg`, `png` | Formato / extensão do arquivo de imagem |
| `orientacao` | `horizontal`, `vertical`, `quadrada` | Orientação espacial da imagem (largura vs. altura) |
| `cor` | `colorida`, `pb` | Identificação do espaço de cor (colorida ou tons de cinza / preto e branco) |
| `tamanho` | `grande`, `media`, `pequena` | Classificação por resolução:<br>• **Grande:** maior lado $\ge$ 1920px<br>• **Pequena:** maior lado $\le$ 400px<br>• **Média:** valores intermediários |
| `peso` | `leve`, `moderada`, `pesada` | Tamanho do arquivo em disco:<br>• **Leve:** $< 100\text{ KB}$<br>• **Moderada:** $100\text{ KB} - 2\text{ MB}$<br>• **Pesada:** $> 2\text{ MB}$ |
| `ano` | Ex: `2024`, `2025`, `2026` | Ano da ultima modificacao registrada no arquivo |

> Termos de busca por metadados em busca livre

| Metadado | Termos que Caem na Busca Livre |
| :--- | :--- |
| `formato` | `jpeg`, `png` *(nome do formato reportado pelo Pillow, sempre em minúsculo)* |
| `dimensões` | • `{largura}x{altura}` (ex: `1920x1080`)<br>• Largura isolada (ex: `1920`)<br>• Altura isolada (ex: `1080`) |
| `orientação` | • `paisagem`, `horizontal` *(se largura > altura)*<br>• `retrato`, `vertical` *(se altura > largura)*<br>• `quadrada` *(se largura == altura)* |
| `porte` *(resolução)* | • `grande` *(maior lado $\ge$ 1920px)*<br>• `media` *(maior lado entre 400px e 1920px)*<br>• `pequena` *(maior lado $\le$ 400px)* |
| `cor` | • Modo Pillow cru: `rgb`, `rgba`, `l`, `cmyk`, etc.<br>• Se P&B / cinza: `preta`, `branca`, `pb`, `bw`, `cinza`, `grayscale`<br>• Se colorida: `colorida`, `cor`, `color` |
| `peso do arquivo` | • `leve` *(menor que 100 KB)*<br>• `moderada` *(entre 100 KB e 2 MB)*<br>• `pesada` *(maior que 2 MB)* |
| `ano de modificação` | Ano numérico puro (ex: `2024`, `2025`, `2026`) |

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
