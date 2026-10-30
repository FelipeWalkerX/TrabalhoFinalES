# Trabalho Final - Engenharia de Software

## Integrantes
- Allan Felipe da Silva - 2269333
- Pedro Henrique dos Santos - 2368030

## Sprint 1 - Definição da Proposta

### Descrição do sistema
O Garage Burger tem várias TVs que passam clipes de música, futebol e NBA, mas hoje não existe nenhum critério para escolher o que vai passar em cada uma, e a caixinha de sugestões vive cheia de reclamação de cliente que não curtiu o que estava passando no momento. A nossa ideia é ajudar o gerente a decidir o que colocar nas TVs com base no que os clientes realmente querem ver. Para isso, os clientes respondem um formulário rápido pelo QR code das mesas, dizendo o que estava passando, se gostaram e o que gostariam de ver. As respostas são exportadas em um CSV, que é a entrada do sistema. O sistema confere os dados, separa as respostas por dia e horário e calcula a aceitação de cada tipo de conteúdo. No final, gera um relatório com o que agradou e o que não agradou em cada horário e uma sugestão de programação para as TVs.

### Pesquisa que justifica o sistema
**Referência:** MALCMAN, M.; AZAR, O. H.; SHAVIT, T.; ROSENBOIM, M. How does background music affect dining duration, tips and bill amounts in restaurants? A field experiment. *Behavioral Sciences*, v. 14, n. 12, art. 1188, 2024. DOI: 10.3390/bs14121188.

**Resumo:**

O estudo em questao foi feito em um restaurante italiano em Telavive, em Israel. Os pesquisadores acompanharam 282 mesas, de uma ou duas pessoas, sem que os clientes soubessem, e compararam três situações: música lenta, música rápida e a playlist normal da casa. Com música lenta, o pessoal ficou em média 80 minutos no restaurante, enquanto com música rápida ficou só 57, ou seja, quase 40% a mais de tempo. Com música rápida, as gorjetas foram um pouco maiores do que com a playlist normal, e o valor da conta não mudou em nenhum dos casos.

O que a gente tira disso é que o que está tocando no ambiente muda o comportamento do cliente, mesmo quando ele nem está prestando atenção. No Garage Burger acontece algo parecido: as TVs passam clipes, futebol e NBA sem nenhum critério, e a caixinha de sugestões mostra que muita gente não curte o que está passando, principalmente certos estilos de música e esportes que quase ninguém acompanha aqui, como NFL e a liga americana de beisebol.

Se o conteúdo interfere no tempo que o cliente fica e na experiência dele, escolher a programação no “achismo” pode fazer o restaurante perder cliente. Por isso a ideia do nosso sistema é pegar as respostas do formulário que os clientes preenchem pelo QR code e mostrar o que agrada e o que não agrada em cada dia e horário, para o gerente montar a programação das TVs com base no que o público realmente quer.
