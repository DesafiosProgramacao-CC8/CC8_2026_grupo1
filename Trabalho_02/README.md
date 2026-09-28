<div align="center">

<img src="assets/IffarQL.svg" alt="IFFARQL" height="220">

Trabalho Integrador 2 · Desafios de Programação · Bacharelado em Ciência da Computação
· IFFar — _Campus_ Frederico Westphalen

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-gerenciador-DE5FE9?logo=uv&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-25%20testes-0A9EDC?logo=pytest&logoColor=white)
![Dependências](https://img.shields.io/badge/runtime-só%20stdlib-2f6faf)

</div>

---

### Alunos

- Cauã Felipe Ziotti Tamiozzo
- Diego Breskovit Morcelli
- Talita Vargas de Souza

### Índice

1. [Introdução](#introdução)
2. [Como executar](#como-executar)
3. [Tecnologias utilizadas](#tecnologias-utilizadas)
4. [Estrutura de pastas](#estrutura-de-pastas)
5. [Arquitetura em camadas](#arquitetura-em-camadas)
6. [Polimorfismo dinâmico](#polimorfismo-dinâmico)
7. [Estrutura de dados utilizada](#estrutura-de-dados-utilizada)
8. [Tipos de dados e operadores](#tipos-de-dados-e-operadores)
9. [Comandos da linguagem](#comandos-da-linguagem)
10. [Transações e ACID](#transações-e-acid)
11. [Limitações conhecidas](#limitações-conhecidas)
12. [Requisitos implementados](#requisitos-implementados)

## Introdução

O IFFARQL é um **Sistema Gerenciador de Banco de Dados simplificado** operado
por terminal. No lugar do SQL tradicional, o usuário digita comandos de uma
variante em português (`CRIATABELA`, `INSERIREM`, `MOSTRADADOSDE`) e o
sistema reconhece a palavra reservada, executa a operação e devolve o
resultado ou o motivo da recusa.

São oito operações de banco: criar e apagar tabela, inserir, atualizar,
remover e mostrar registros, salvar e carregar o banco. Além delas o terminal
aceita `AJUDA`, que lista a sintaxe de cada comando, e `SAIR`, que são conveniências
da interface, não operações de banco.

Os registros de cada tabela não ficam num vetor: ficam numa **árvore digital
indexada pelo `id`**. Consultas por `id` descem direto até o nó, as demais percorrem a
árvore inteira.

## Como executar

O projeto usa o [UV](https://docs.astral.sh/uv/). Depois de instalado, navegue
até `Trabalho_02/`:

```bash
uv run python main.py
```

> O `uv run` já cria o ambiente virtual e baixa o Python 3.14. O sistema não
> tem nenhuma dependência de runtime, só a biblioteca padrão. Para preparar o
> ambiente sem executar nada, use `uv sync`.

Com o terminal no ar:

1. Digite `AJUDA` para ver a sintaxe dos oito comandos e os tipos aceitos.
2. Carregue a amostra pronta deste repositório:
   `CARREGARIFFARQL iffarql_revenda_carros.txt`
3. Consulte: `MOSTRADADOSDE carro ONDE preco < 70000`
4. `SAIR` encerra.

Como rodar os testes unitários:

```bash
uv run pytest
```

## Tecnologias utilizadas

| Tecnologia        | Papel no projeto                                                      |
| :---------------- | :-------------------------------------------------------------------- |
| **Python 3.14**   | Linguagem base                                                        |
| **uv**            | Gerenciador de ambiente e dependências (`pyproject.toml` + `uv.lock`) |
| **pytest**        | Suíte de 25 testes (dependência apenas de desenvolvimento)            |
| `re`              | Tokenização da linha de comando e validação dos literais              |
| `json`            | Formato de persistência do banco em disco                             |
| `operator`        | Tabela de operadores aritméticos e de comparação dos tipos            |
| `contextlib`      | `Banco.transacao()` como gerenciador de contexto                      |
| `os` / `tempfile` | Troca atômica do arquivo salvo e arquivo temporário do auto-salvar    |

Nenhuma biblioteca de estrutura de dados foi utilizada: a árvore é
implementada integralmente pelo grupo em `iffarql/arvore.py`.

## Estrutura de pastas

```
Trabalho_02/
├── main.py                     # REPL: prompt, transacao por comando, tratamento de erro
├── iffarql/
│   ├── erros.py                # ErroIffarql: a unica excecao que o REPL converte em aviso
│   ├── lexer.py                # tokenizar(): linha crua -> lista de tokens
│   ├── comandos.py             # as oito subclasses de Comando + interpretar()
│   ├── terminal.py             # cores ANSI, moldura da tabela, logo, AJUDA
│   ├── tipos.py                # Tipo e as cinco subclasses (INTEIRO, DECIMAL, ...)
│   ├── expressoes.py           # Coluna, Esquema, Condicao (ONDE), Atribuicao (COM)
│   ├── arvore.py               # a arvore de registros indexada por id
│   ├── tabela.py               # esquema, conversao de valores, selecionar/atualizar/apagar
│   └── banco.py                # tabelas, integridade referencial, transacao, arquivo
├── test_iffarql.py             # 25 testes de ponta a ponta
├── iffarql_revenda_carros.txt  # amostra para CARREGARIFFARQL
├── assets/IffarQL.svg
└── T2.pdf
```

## Arquitetura em camadas

O sistema é dividido em três camadas. **A dependência é sempre para baixo**:
nenhum módulo importa algo de uma camada acima da sua, o que mantém as regras
de banco independentes do formato do comando digitado e da aparência da saída.

| #   | Camada                     | Módulos                                             | Responsabilidade                                                                                                            |
| :-- | :------------------------- | :-------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Entrada e apresentação** | `lexer.py`, `comandos.py`, `terminal.py`, `main.py` | Quebrar a linha em tokens, escolher a classe da palavra reservada, montar o objeto do comando e desenhar a saída.           |
| 2   | **Tipagem e expressões**   | `tipos.py`, `expressoes.py`                         | Os cinco tipos e os operadores que cada um aceita; conversão de literal para valor; avaliação do `ONDE` e cálculo do `COM`. |
| 3   | **Núcleo do banco**        | `arvore.py`, `tabela.py`, `banco.py`                | Armazenamento dos registros, esquema, integridade referencial, transação e arquivo.                                         |

### Responsabilidade de cada módulo

| Módulo          | Faz                                                                                           | Não faz                               |
| :-------------- | :-------------------------------------------------------------------------------------------- | :------------------------------------ |
| `lexer.py`      | Linha → tokens, preservando aspas e isolando parênteses.                                      | Não conhece palavra reservada.        |
| `comandos.py`   | Uma subclasse por palavra reservada: `de_tokens()` monta o objeto, `executar()` aplica.       | Não valida tipo nem regra de negócio. |
| `terminal.py`   | Cor, moldura da tabela, logo e tela de `AJUDA`.                                               | Não importa nada do projeto.          |
| `tipos.py`      | Os cinco tipos: `converter`, `formatar`, `operar`, `comparar`, cada um com seus operadores.   | Não sabe o que é tabela ou registro.  |
| `expressoes.py` | `Coluna` (esquema), `Condicao` (`ONDE`) e `Atribuicao` (`COM`), avaliadas contra um registro. | Não acessa a árvore nem o banco.      |
| `arvore.py`     | Registros indexados por `id`: inserir, buscar, remover, percorrer.                            | Não conhece esquema nem tipo.         |
| `tabela.py`     | Esquema, conversão do `INSERIREM`, `proximo_id`, consulta e JSON.                             | Não valida chave estrangeira.         |
| `banco.py`      | Tabelas, integridade referencial, transação, salvar e carregar.                               | Não faz parsing nem formatação.       |
| `main.py`       | O REPL: lê a linha, abre transação quando altera dados, imprime.                              | Não contém lógica de comando.         |

### Fluxo de um comando

```
main.repl()
   │
   ├─ comandos.interpretar(linha)
   │     ├─ lexer.tokenizar   ->  ['INSERIREM', 'cliente', 'VALOR', '(', '"Joao"', ...]
   │     └─ COMANDOS['INSERIREM'].de_tokens(resto)  ->  objeto Inserir
   │
   └─ with bd.transacao():      snapshot; rollback no erro; auto-salvar no sucesso
         └─ Inserir.executar(bd)
               └─ banco.Banco.inserir
                     ├─ tabela.converter_valores   -> tipos.Tipo.converter
                     ├─ banco.validar_referencias  -> checa as FKs do registro
                     └─ tabela.inserir             -> arvore.inserir(id, registro)
```

## Polimorfismo dinâmico

Duas hierarquias de classes fazem o papel que seria de cadeias de `if`.

**Um comando, uma classe.** Cada palavra reservada é uma subclasse de
`Comando`, com seu `de_tokens()` (tokens → objeto) e seu `executar()` (objeto →
efeito no banco). Ao ser definida, a subclasse se registra sozinha no
dicionário `COMANDOS`. O interpretador então só busca a classe pelo primeiro
token e chama `executar()`, sem saber qual das oito respondeu.

**Um tipo, uma classe.** Cada tipo é uma subclasse de `Tipo`, com seu
`converter()`, `comparar()` e `operar()`, e declara quais operadores aceita. A
tabela de operadores do enunciado virou esses conjuntos: a classe base recusa o
que está fora e cada subclasse implementa o seu comportamento: `Inteiro`
divide truncando, `Texto` concatena no `+`, `Data` soma dias.

Em ambos os casos, incluir um comando ou um tipo novo é escrever uma subclasse;
nenhum código existente muda.

## Estrutura de dados utilizada

Os registros de cada tabela ficam numa **árvore digital (trie de dígitos)**
implementada em `iffarql/arvore.py`. A chave do nó é a
coluna `id`, preenchida com zeros à esquerda até dez dígitos; o registro
completo fica no nó do último dígito, como informação auxiliar. O
`id 42`, por exemplo, é o caminho `0 → 0 → 0 → 0 → 0 → 0 → 0 → 0 → 4 → 2`.

A escolha se apoia em três pontos:

- **Profundidade constante.** Todo `id` ocupa dez dígitos, então a altura é
  fixa: inserir, buscar e remover custam dez passos, com dez ou dez milhões de
  registros. Não há rebalanceamento nem o caso degenerado de uma árvore binária
  alimentada com ids crescentes, que viraria uma lista.

- **Ordem de `id` sai de graça.** Visitando os dígitos em ordem crescente,
  `percorrer()` devolve os registros já ordenados por `id`, sem ordenação
  posterior. É uma DFS iterativa, sem recursão, e um gerador.

- **Remoção sem lixo.** Ao remover, a árvore sobe pelo caminho apagando todo nó
  que ficou sem registro e sem filhos, então não acumula caminhos mortos.


## Tipos de dados e operadores

| Tipo       | Representação interna        | Literal aceito     |
| :--------- | :--------------------------- | :----------------- |
| `INTEIRO`  | `int`                        | `20`, `-3`         |
| `DECIMAL`  | `float`, exibido com 2 casas | `1.80`, `64990.00` |
| `BOOLEANO` | `bool`                       | `true`, `false`    |
| `TEXTO`    | `str` sem acentos            | `"Nome Sobrenome"` |
| `DATA`     | tupla `(dia, mês, ano)`      | `"20/10/2010"`     |

## Comandos da linguagem

| Comando           | Sintaxe                                                                  |
| :---------------- | :----------------------------------------------------------------------- |
| `CRIATABELA`      | `<tabela> ( <coluna> <TIPO> [INTEIRO CHAVESTRANGEIRA <tabela>] ... )`    |
| `APAGATABELA`     | `<tabela>`                                                               |
| `INSERIREM`       | `<tabela> VALOR ( <valor> ... )`                                         |
| `ATUALIZATABELA`  | `<tabela> COM <coluna> = <valor> [COM ...] [ONDE <coluna> <op> <valor>]` |
| `APAGADADOSDE`    | `<tabela> [ONDE <coluna> <op> <valor>]`                                  |
| `MOSTRADADOSDE`   | `<tabela> [ONDE <coluna> <op> <valor>]`                                  |
| `SALVARBD`        | `<arquivo>`                                                              |
| `CARREGARBD`      | `<arquivo>`                                                              |
| `CARREGARIFFARQL` | `<arquivo.txt>`                                                          |

## Transações e ACID

**Atomicidade.** Todo comando que altera dados roda dentro de
`Banco.transacao()`, que tira um retrato do banco antes de começar e qualquer
erro durante a transação restaura o retrato e vira um aviso no terminal. 

**Consistência.** Tipos e chaves estrangeiras são validados antes da
gravação, nunca durante.

**Isolamento.** _dispensado pelo enunciado_

**Durabilidade.** Ao fim de toda transação bem-sucedida o banco é salvo
automaticamente, no arquivo do último `SALVARBD`/`CARREGARBD` ou num
temporário no formato JSON.

## Limitações conhecidas

| Limitação                              | Detalhe                                                                                                                                                                     |
| :------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Um comparador por `ONDE`**           | O enunciado dispensa combinações: não há `E`/`OU`, e a condição é sempre `<coluna> <op> <valor>`                                                                            |
| **Sem `JOIN`, ordenação ou agregação** | `MOSTRADADOSDE` lê uma tabela por vez, em ordem de `id`. Não há `ORDER BY`, `COUNT` ou consulta entre tabelas                                                               |
| **Anos bissextos**                     | Desconsiderados por exigência do enunciado: fevereiro tem sempre 28 dias, o ano tem sempre 365                                                                              |
| **Acentuação em `TEXTO`**              | Removida na conversão, então `"Adão"` é gravado e pesquisado como `Adao`                                                                                                    |
| **Divisão de `INTEIRO`**               | `/` entre inteiros trunca (`7 / 2` = 3), preservando o tipo da coluna em vez de promover para decimal                                                                       |
| **Custo da transação**                 | O rollback usa um retrato completo das tabelas por comando: barato no volume deste trabalho, caro se o banco crescer muito. Um journal resolveria, e está marcado no código |
| **Consultas fora do `id`**             | Não há índice secundário: qualquer condição que não seja `id ==` percorre a árvore inteira                                                                                  |
| **Limite do `id`**                     | Dez dígitos, ou seja, até 9.999.999.999 registros por tabela                                                                                                                |
| **`CARREGARBD` exige banco vazio**     | Não é possível mesclar um arquivo a um banco já em uso                                                                                                                      |
| **Sem concorrência**                   | O terminal é de acesso único e não há bloqueio de arquivo                                                                                                                   |
| **Parênteses e nomes**                 | Parênteses aninhados não são aceitos, e nomes de tabela e coluna não são checados contra as palavras reservadas                                                             |

## Requisitos implementados

| #   | Objetivo                                              | Onde                                                           |
| :-- | :---------------------------------------------------- | :------------------------------------------------------------- |
| 1   | Criar tabela, com `id` automático e `CHAVESTRANGEIRA` | `comandos.py::CriaTabela` + `banco.criar_tabela`               |
| 2   | Apagar tabela, só se não houver registros             | `comandos.py::ApagaTabela` + `banco.apagar_tabela`             |
| 3   | Inserir registros com validação de ordem e tipo       | `comandos.py::Inserir` + `tabela.converter_valores`            |
| 4   | Atualizar registros, com cálculo sobre a coluna       | `comandos.py::Atualizar` + `expressoes.Atribuicao`             |
| 5   | Remover registros, com ou sem condição                | `comandos.py::ApagaDados` + `banco.apagar_dados`               |
| 6   | Mostrar registros, todos os campos e o `id`           | `comandos.py::MostraDados` + `terminal.tabelar`                |
| 7   | Salvar o banco em arquivo                             | `banco.salvar` (JSON + troca atômica)                          |
| 8   | Carregar o banco salvo                                | `banco.carregar` + `tabela.de_dict`                            |
| 8.1 | Carregar e executar um `.txt` de comandos             | `comandos.py::CarregarIffarql`                                 |
| 9   | Cinco tipos de dados                                  | `tipos.py` (`Inteiro`, `Decimal`, `Booleano`, `Texto`, `Data`) |
| 10  | Tabela de operadores por tipo                         | Atributos `operadores_aritmeticos` / `operadores_comparacao`   |
| 11  | Aritmética de datas em dias                           | `tipos.py::Data._operar`                                       |
| 12  | Registros em árvore, com `id` como chave do nó        | `arvore.py` + `tabela.Tabela.arvore`                           |
| 13  | Integridade referencial 1:N                           | `banco.validar_referencias` e `banco.referenciam`              |
| 14  | `proximo_id` preservado no salvar/carregar            | `tabela.para_dict` / `tabela.de_dict`                          |
| 15  | Transações atômicas com rollback                      | `banco.transacao`                                              |
| 16  | Durabilidade por auto-salvamento                      | `main.executar_linha` + `Comando.altera_dados`                 |
| 17  | Orientação a objetos com polimorfismo dinâmico        | `Comando` e subclasses; `Tipo` e subclasses                    |
| 18  | Documentação do trabalho                              | Este README                                                    |
