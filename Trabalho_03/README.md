# IFFARCHAT

<!-- Introdução (entregável 1): escrita em conjunto no final. -->

<!-- Tecnologias (entregável 2): parte do B. -->

<!-- Hash da senha (entregável 3): parte do C. -->

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

<!-- Telas do programa (entregável 5): parte do C. -->

## Limitações conhecidas

<!-- B e C acrescentam aqui as limitações do servidor e do cliente. -->

- **29 de fevereiro:** o IFFARQL do Trabalho 2 considera fevereiro sempre com 28
  dias. Nascimentos em 29/02 são recusados no cadastro, e mensagens privadas
  enviadas num dia 29/02 não podem ser gravadas.
- **Gravação do arquivo inteiro:** cada alteração regrava todo o arquivo JSON do
  banco. É adequado ao volume de um trabalho acadêmico, mas ficaria lento com
  milhares de mensagens.
- **Fila única:** todas as operações do banco são executadas uma por vez. Com
  muitos usuários simultâneos, a fila é o gargalo do servidor.
