# IFFARCHAT

<!-- Introdução (entregável 1): escrita em conjunto no final. -->

<!-- Tecnologias (entregável 2): parte do B. -->

## Hash da senha

A senha nunca viaja em texto puro: o cliente calcula um hash e envia só o
resultado. O servidor guarda e compara essa string sem saber como ela foi
gerada. Dos algoritmos permitidos pelo enunciado, escolhemos o **FNV-1a de 32
bits** (Fowler–Noll–Vo), porque é o mais curto de todos: duas operações por
byte, sem tabelas nem rotações, o que torna fácil mostrar o cálculo passo a
passo. A implementação está em `senha.py`, sem nenhuma biblioteca de hash.

### Algoritmo

```
h = 0x811C9DC5                    # valor inicial ("offset basis")
para cada byte b da senha em UTF-8:
    h = h XOR b                   # 1. mistura o byte nos bits baixos
    h = (h * 0x01000193) mod 2^32 # 2. espalha para os bits altos (primo do FNV)
resultado = h em 8 dígitos hexadecimais
```

O "1a" no nome indica a ordem das operações: XOR primeiro, multiplicação
depois (no FNV-1 original é o contrário). Essa ordem melhora a dispersão para
entradas pequenas, como senhas de 6 caracteres. O `mod 2^32` é feito com uma
máscara (`& 0xFFFFFFFF`), porque o Python não limita o tamanho dos inteiros.

### Exemplo passo a passo: `abc123`

| byte | caractere | h após XOR | h após × primo |
| ---: | :-------: | :--------- | :------------- |
|   97 |    `a`    | `811c9da4` | `e40c292c`     |
|   98 |    `b`    | `e40c294e` | `4d2505ca`     |
|   99 |    `c`    | `4d2505a9` | `1a47e90b`     |
|   49 |    `1`    | `1a47e93a` | `9934264e`     |
|   50 |    `2`    | `9934267c` | `a9189534`     |
|   51 |    `3`    | `a9189507` | `38b29a05`     |

Resultado: `abc123` → **`38b29a05`**. É isso que vai no campo senha do
`REGISTRAR` e do `AUTENTICAR`. Rodar `python senha.py` imprime essa tabela.

Mais exemplos de entrada e saída:

| Entrada  | Saída      | Observação                                              |
| :------- | :--------- | :------------------------------------------------------ |
| `abc123` | `38b29a05` |                                                         |
| `abc124` | `31b28f00` | um byte diferente muda a saída inteira                  |
| `senha1` | `94c7098d` |                                                         |
| `Senha1` | `5d55b62d` | maiúscula e minúscula são bytes diferentes              |
| `""`     | `811c9dc5` | nenhum byte: sai o valor inicial (vetor oficial)        |
| `a`      | `e40c292c` | vetor oficial                                           |
| `foobar` | `bf9cf968` | vetor oficial                                           |

As três últimas linhas são os vetores de teste publicados pelos autores do
FNV. Como não existe FNV-1a na biblioteca padrão do Python para servir de
"biblioteca de referência", são esses vetores que fazem a comparação:
`senha.py` termina com uma auto-checagem deles e `test_senha.py` os verifica.

### Regras em volta do hash

- **Formato na rede:** 8 dígitos hexadecimais minúsculos. O enunciado mostra
  `AAAArgAKAg==` (Base64) só como ilustração; como o servidor apenas compara
  strings, qualquer formato funciona.
- **Senha exigida no cadastro:** exatamente 6 caracteres alfanuméricos ASCII
  (`senha_valida`). No login o cliente não valida: envia o hash do que foi
  digitado, para conseguir entrar em servidores de outros grupos que tenham
  aceitado outra regra no cadastro.
- **Onde é calculado:** só no cliente, antes de enviar. O servidor nunca vê a
  senha original. `ATUALIZARPERFIL` manda o mesmo hash para confirmar a
  identidade; a senha não muda.
- **Não é criptografia:** FNV-1a foi feito para tabelas hash, não para
  senhas. Em 32 bits há só 4 bilhões de saídas e nenhum sal. Atende ao
  propósito didático do trabalho, não a um sistema real.

## Banco de dados

O IFFARCHAT guarda usuários, amizades e conversas privadas no IFFARQL, o banco
desenvolvido no Trabalho 2. O chat geral não é gravado: existe só em memória,
enquanto há gente online.

### Script IFFARQL (`esquema.iffarql`)

```
CRIATABELA usuario ( nome_completo TEXTO apelido TEXTO data_nascimento DATA senha TEXTO )
CRIATABELA amizade ( id_usuario_1 INTEIRO CHAVESTRANGEIRA usuario id_usuario_2 INTEIRO CHAVESTRANGEIRA usuario bloqueado BOOLEANO ha_notificacao BOOLEANO aceita BOOLEANO ultima_lida INTEIRO )
CRIATABELA conversa ( id_amizade INTEIRO CHAVESTRANGEIRA amizade data DATA hora INTEIRO minuto INTEIRO mensagem TEXTO )
```

O `id` de cada tabela é criado automaticamente pelo IFFARQL. Na primeira vez que
o servidor sobe, ele executa este script e salva o banco em `dados/iffarchat.json`;
nas seguintes, apenas carrega esse arquivo.

**Duas linhas por amizade.** Uma amizade entre Ana e Beto gera as linhas
(Ana, Beto) e (Beto, Ana). Cada linha pertence a quem está em `id_usuario_1`, e
suas colunas descrevem o ponto de vista do dono:

| Coluna           | Na linha da Ana significa                                   |
| :--------------- | :---------------------------------------------------------- |
| `bloqueado`      | Ana silenciou o Beto (o Beto não é afetado)                 |
| `ha_notificacao` | Ana tem algo novo do Beto: um pedido de amizade ou mensagem |
| `aceita`         | o pedido já foi aceito (igual nas duas linhas)              |
| `ultima_lida`    | `id` da última mensagem do Beto já entregue à Ana           |

Um pedido de amizade cria as duas linhas com `aceita` falso, e só a linha de
quem recebeu o pedido fica com `ha_notificacao` verdadeiro. É isso que identifica
quem pediu a quem. Aceitar marca as duas linhas; recusar apaga as duas.

**Extensões ao modelo mínimo do enunciado.** As colunas `aceita` e `ultima_lida`
foram acrescentadas. Sem `aceita`, a coluna `bloqueado` teria de significar ao
mesmo tempo "pedido pendente" e "silenciado", e um booleano não distingue as duas
coisas. `ultima_lida` é um cursor gravado no banco: garante que a mesma mensagem
não seja entregue duas vezes, mesmo que o servidor reinicie.

**Conversas.** Cada mensagem aponta (`id_amizade`) para a linha de quem a enviou.
O histórico entre Ana e Beto é a união das mensagens das duas linhas, ordenada
pelo `id`. A ordem é pelo `id`, e não pela hora, porque o banco não guarda
segundos: duas mensagens no mesmo minuto empatariam, e o `id` só cresce.

**Textos.** O tipo `TEXTO` do IFFARQL remove acentos e não aceita aspas. Para que
nomes e mensagens voltem exatamente como foram escritos, todo texto é codificado
com `urllib.parse.quote` antes de gravar (`João "Zé"` vira
`Jo%C3%A3o%20%22Z%C3%A9%22`) e decodificado com `unquote` ao ler.

### Fila de acesso ao banco

O servidor atende cada cliente numa thread própria, mas o IFFARQL não foi feito
para ser usado por várias threads ao mesmo tempo. Sem controle, duas pessoas
registrando o mesmo apelido no mesmo instante poderiam ambas verificar que ele
está livre e ambas inserir, duplicando o apelido.

A solução é uma fila com um único consumidor:

```
thread do cliente 1 ──┐
thread do cliente 2 ──┼──> [ fila FIFO ] ──> trabalhador-bd ──> Banco (IFFARQL)
thread do cliente 3 ──┘         ^                  │
                                └─── resultado ────┘ (via Future)
```

1. Uma única thread, `trabalhador-bd`, é dona do objeto do banco. Nenhuma outra
   thread o acessa.
2. Para usar o banco, a thread de um cliente coloca na fila (`queue.Queue`) a
   operação a executar, junto com um `Future`, e fica esperando o resultado nele.
3. O trabalhador retira um pedido por vez, na ordem de chegada, e o executa.
   Operações que alteram dados rodam dentro de uma transação do IFFARQL: se algo
   falhar no meio, tudo é desfeito; se der certo, o arquivo é salvo.
4. O trabalhador entrega o resultado, ou o erro, pelo `Future`, e a thread do
   cliente continua.

Garantias que isso traz:

- **Exclusão mútua:** como só uma thread executa operações, duas operações nunca
  se intercalam. "Verificar se o apelido está livre e inserir" é um único pedido,
  e ninguém consegue registrar o mesmo apelido entre as duas etapas.
- **Ordem:** os pedidos são atendidos na ordem em que chegaram.
- **Atomicidade:** operações com várias etapas, como criar as duas linhas de uma
  amizade, acontecem por inteiro ou não acontecem.
- **Durabilidade:** toda alteração é gravada em disco antes de o cliente receber
  a resposta.

Consultas que apenas leem (login, perfil, lista de amigos, notificações) também
passam pela fila, mas sem transação: não há o que desfazer nem salvar. Isso
importa porque cada cliente verifica notificações a cada 2 segundos, e regravar
o arquivo a cada verificação deixaria a fila lenta para todos.

Os testes em `test_dados.py` verificam essas garantias, entre elas com 20 threads
concorrentes atualizando o mesmo dado sem perder nenhuma atualização.

## Cliente e telas do programa

O cliente (`cliente.py`) roda no terminal e só usa a biblioteca padrão.
Para iniciar:

```
uv run python cliente.py            # host padrão: localhost
uv run python cliente.py 10.0.0.5   # servidor de outra máquina (porta 42000)
```

Ele tem três estados: DESCONECTADO, CONECTADO (socket aberto, sem login) e
LOGADO. Cada estado tem um menu numerado; `0` sempre é a opção de sair do
estado atual.

**Como ele conversa com o servidor.** O cliente manda um pedido por vez e lê
quadros até chegar a resposta esperada ou um `32768`. Qualquer outro quadro
que apareça no meio (um `257` de pedido de amizade, um `259` de resposta ou
algo que outro grupo tenha inventado) vai para o tratador de notificações e a
leitura continua. Assim o cliente funciona com servidores que enviam
notificações por conta própria e com os que só respondem a pedidos. Enquanto
está logado, uma thread faz as requisições periódicas exigidas pelo enunciado,
a cada 2 segundos: `128` (notificações) sempre e `1024` (novas mensagens)
quando há uma conversa aberta. Se o servidor demorar mais de 5 segundos ou
fechar o socket, o cliente avisa e volta para DESCONECTADO.

Os quadros `256` e `258` não têm resposta de sucesso no enunciado. Para não
ficar esperando, o cliente os envia seguidos de um `PING`: se um `32768`
chegar antes do `PONG`, é o erro do pedido; se chegar só o `PONG`, deu certo.

### Desconectado e conectado

```
=== IFFARCHAT ===

--- DESCONECTADO ---
1. Conectar
0. Sair
> 1
host [localhost]:
conectado a localhost:42000

--- CONECTADO ---
1. Registrar
2. Entrar
0. Desconectar
> 1
nome completo: Ana Souza
apelido: ana
nascimento (DD/MM/AAAA): 10/05/2000
senha (6 letras ou números):
registrado! agora use 'Entrar'.
```

A senha é lida sem eco. Nome, apelido e nascimento são recusados na hora se
contiverem `|` ou quebra de linha; a senha, se não tiver exatamente 6
caracteres alfanuméricos.

### Login e menu principal

```
--- CONECTADO ---
1. Registrar
2. Entrar
0. Desconectar
> 2
apelido: ana
senha:
bem-vindo, ana (id 1)

[sem notificações]

--- LOGADO como ana ---
1. Chat geral
2. Quem está online
3. Meus amigos
4. Pedidos de amizade
5. Adicionar amigo
6. Conversa privada
7. Silenciar/dessilenciar amigo
8. Ver perfil
9. Editar meu perfil
0. Logoff
> 2
online:
     2  beto
```

Senha errada mostra o erro do servidor e volta ao menu:

```
> 2
apelido: caio
senha:

erro do servidor (ERROAUTENTICACAO): Senha invalida
```

### Notificações

A linha entre colchetes, reimpressa antes de cada menu, é a barra de
notificações. Ela cobre os dois casos do enunciado: mensagens privadas não
lidas (quem enviou, sem o conteúdo) e pedidos de amizade aguardando resposta.
Além disso, mostra uma vez as respostas aos pedidos que o usuário fez.

```
[novas mensagens: ana | pedidos de amizade: 1]
```

Quando o servidor envia um `257` ou `259` enquanto o usuário está no menu,
o aviso aparece na hora, acima do prompt:

```
--- LOGADO como beto ---
...
0. Logoff

[pedido de amizade de ana]
> 4
ana quer ser seu amigo. aceitar? [s/n/pular] s
aceito
```

Do lado de quem pediu:

```
> 5
online:
     2  beto
id do usuário (vazio para cancelar): 2
pedido de amizade enviado para beto

[beto aceitou sua amizade]
> 3
amigos:
     2  beto

[respostas: beto aceitou]
```

### Conversa privada

Ao abrir uma conversa, o cliente pede o histórico (`4096`) e o mostra; depois
cada linha digitada vira um `2048`, e as respostas chegam pela verificação
periódica. `/sair` volta ao menu.

```
> 6
amigos:
     1  ana
id do amigo (vazio para cancelar): 1
--- conversa com ana ---
[15/11/2026 20:48] ana: oi beto!
(digite /sair para voltar ao menu)
oi ana, tudo bem?
[15/11/2026 20:48] eu: oi ana, tudo bem?
/sair
```

### Chat geral

Igual à conversa privada, mas sem histórico: só chega o que for enviado
enquanto o usuário está online.

```
> 1
--- chat geral ---
(digite /sair para voltar ao menu)
olá geral
[15/11/2026 20:48] eu: olá geral
[15/11/2026 20:48] beto: oi geral, sou o beto
/sair
```

### Perfil e silenciamento

```
> 8
id do usuário [1]: 2
id: 2
nome: Beto Lima
apelido: beto
idade: 25

> 9
novo nome completo: Ana Souza Lima
novo nascimento (DD/MM/AAAA): 10/05/2000
senha atual (para confirmar):
perfil atualizado

> 7
amigos:
     2  beto
id do amigo (vazio para cancelar): 2
silenciamento de beto alterado
```

### Conexão perdida

Se o servidor cair, a thread de verificação percebe e o cliente volta ao
estado desconectado, como exige o enunciado:

```
--- LOGADO como caio ---
...
0. Logoff

conexão com o servidor perdida
(pressione Enter)
>

--- DESCONECTADO ---
1. Conectar
0. Sair
```

## Limitações conhecidas

<!-- B acrescenta aqui as limitações do servidor. -->

- **Atraso de até 2 segundos:** notificações e mensagens novas chegam pela
  verificação periódica. O que o servidor envia por conta própria (`257`,
  `259`) só é lido quando o cliente faz o próximo pedido.
- **Chat geral só na tela do chat:** mensagens do chat geral enviadas enquanto
  o usuário está no menu ficam no servidor e aparecem quando ele entra no chat.
  O enunciado não define notificação para o chat geral.
- **Silenciar é "cego":** o `513` não informa se a conversa ficou silenciada
  ou não. O cliente só confirma que o estado foi invertido.
- **Pedidos de amizade sem confirmação:** o enunciado não define resposta de
  sucesso para `256` e `258`. O cliente usa um `PING` em seguida para saber se
  houve erro.
- **Hash incompatível entre grupos:** o servidor compara a string do hash. Um
  usuário cadastrado pelo cliente de um grupo não consegue entrar pelo cliente
  de outro grupo que use algoritmo ou formato diferente. Vale para todos os
  grupos.
- **Sem reconexão automática:** ao perder a conexão o cliente volta ao estado
  desconectado e o usuário reconecta pelo menu (o enunciado deixa isso como
  opcional).
- **Terminal simples:** sem cores nem limpeza de tela. Uma mensagem que chega
  enquanto o usuário digita aparece na linha de cima do que ele está
  escrevendo.

- **29 de fevereiro:** o IFFARQL do Trabalho 2 considera fevereiro sempre com 28
  dias. Nascimentos em 29/02 são recusados no cadastro, e mensagens privadas
  enviadas num dia 29/02 não podem ser gravadas.
- **Gravação do arquivo inteiro:** cada alteração regrava todo o arquivo JSON do
  banco. É adequado ao volume de um trabalho acadêmico, mas ficaria lento com
  milhares de mensagens.
- **Fila única:** todas as operações do banco são executadas uma por vez. Com
  muitos usuários simultâneos, a fila é o gargalo do servidor.
