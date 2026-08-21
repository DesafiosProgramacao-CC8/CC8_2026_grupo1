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