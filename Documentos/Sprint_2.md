# Sprint 2 - Histórias de usuário e testes

**Projeto:** Analisador da programação das TVs do Garage Burger
**Integrantes:** Allan Felipe da Silva, Pedro Henrique dos Santos e Gabriel Jesus
**Usuário:** o gerente, que escolhe o que passa nas TVs

Nesta sprint a gente escreveu as histórias, os critérios e os testes. As funções ainda não foram implementadas, então os testes falham de propósito (estado RED). A implementação fica para a Sprint 3.

## 1. O que o sistema faz

O sistema lê as respostas que os clientes deixam sobre o que estava passando nas TVs, calcula o quanto cada conteúdo agradou e o que o pessoal gostaria de ver, e gera um relatório para o gerente. Dá para analisar só um período, um dia da semana, uma faixa de horário ou uma TV.

Tudo roda em Python, pelo terminal. Nesta versão a gente trabalha com tipos de conteúdo (rock, pop, sertanejo, futebol e basquete), e não com músicas ou jogos específicos. O formulário com QR code é de onde vêm os dados, mas não faz parte do programa. Também ficam de fora: app para o cliente, tocar música e controlar as TVs.

### De onde vêm os dados

A pesquisa de satisfação que o Garage já tem dá uma nota geral para a música, mas não diz o que estava passando nem o que o cliente preferia. Por isso ela serve para mostrar que o problema existe, mas não dá para usar como entrada do sistema. A entrada vai ser um CSV novo, vindo do formulário do QR code. Enquanto essa coleta não acontece, os testes usam dados inventados, e o arquivo `dados/exemplo_avaliacoes_simuladas.csv` também é só um exemplo.

## 2. Formato do CSV de entrada

CSV em UTF-8, separado por ponto e vírgula (`;`), com cabeçalho na primeira linha. As sete colunas precisam existir, mesmo que uma opcional venha vazia.

| Campo | Tipo depois de importar | Regra |
| --- | --- | --- |
| `id_resposta` | `str` | Não pode ser vazio e não pode repetir. Identifica a resposta, não o cliente. |
| `data_hora` | `datetime` | Formato `AAAA-MM-DDTHH:MM:SS`, horário local. |
| `mesa` | `str` ou `None` | Opcional. Mantém zeros à esquerda (`023`). |
| `tv_id` | `str` | Não pode ser vazio. Ex.: `TV1`. |
| `conteudo_exibido` | `str` | Um dos conteúdos do catálogo. |
| `nota_conteudo` | `int` | Nota inteira de 1 a 5 para o que estava passando. Vazio não vira zero. |
| `preferencia` | `str` ou `None` | Opcional. Um conteúdo do catálogo que o cliente gostaria de ver. |

Catálogo desta versão: `rock`, `pop`, `sertanejo`, `futebol` e `basquete`. Foi uma escolha nossa de escopo.

Ao importar, o sistema tira os espaços das pontas, deixa `conteudo_exibido` e `preferencia` em minúsculas e mantém o `tv_id` como veio. Campo opcional vazio vira `None`.

Exemplo:

```csv
id_resposta;data_hora;mesa;tv_id;conteudo_exibido;nota_conteudo;preferencia
SIM-001;2026-10-30T19:00:00;023;TV1;rock;2;pop
```

Aqui a nota 2 é para o rock, que estava passando. O "pop" é só um voto de preferência, contado separado. Não é uma nota boa para o pop.

## 3. Regras da análise

- **Média:** usa todas as notas válidas daquele conteúdo.
- **Aceitação:** `100 × (notas 4 ou 5) / total de avaliações do conteúdo`.
- **Preferências:** cada resposta com `preferencia` preenchida conta um voto, só dentro do recorte analisado.
- **Mínimo de avaliações:** só entra na recomendação o conteúdo com pelo menos `min_avaliacoes` avaliações (padrão 5, dá para mudar para outro inteiro positivo). Assim o sistema não escolhe com base em uma resposta só.
- **Ordem do ranking:** maior aceitação; se empatar, mais votos de preferência; se ainda empatar, ordem alfabética.
- Um conteúdo que só recebeu votos de preferência, sem avaliações suficientes, aparece na contagem de preferências, mas não entra no ranking.
- Se ninguém atingir o mínimo, o resultado é `dados_insuficientes`, sem conteúdo recomendado e com ranking vazio.
- O sistema só sugere. Quem decide e troca o que passa é o gerente.

## 4. Histórias de usuário e critérios de aceitação

### HU01 - Importar e validar as respostas

**Como gerente do Garage Burger, quero importar um arquivo CSV com as avaliações dos conteúdos, para analisar as respostas sem precisar organizar cada registro na mão.**

| Critério | Condição verificável |
| --- | --- |
| HU01-CA01 | Com um CSV válido, importar todas as linhas, converter data e nota para os tipos certos, normalizar os textos e deixar mesa e preferência vazias como `None`, sem nenhum erro. |
| HU01-CA02 | Se faltar alguma das sete colunas no cabeçalho, parar a importação com `ValueError`, dizendo qual coluna falta. |
| HU01-CA03 | Se uma linha tiver ID vazio, data inválida, TV vazia, conteúdo fora do catálogo, nota vazia ou fora de 1 a 5 (ou não inteira), ou preferência fora do catálogo, rejeitar só essa linha, informando o número dela e o campo errado, e continuar com as outras. O cabeçalho é a linha 1. |
| HU01-CA04 | Se um ID já importado aparecer de novo, manter a primeira ocorrência válida e rejeitar a repetida, registrando a linha e o campo `id_resposta`. Uma linha que já foi rejeitada não "reserva" o ID. |

### HU02 - Escolher o recorte da análise

**Como gerente do Garage Burger, quero filtrar as avaliações por período, dia da semana, faixa de horário e TV, para decidir a programação de um momento específico.**

| Critério | Condição verificável |
| --- | --- |
| HU02-CA01 | Com início e fim, incluir as respostas no instante inicial e excluir as do instante final (`inicio <= data_hora < fim`), sem alterar a lista original e mantendo a ordem. Se um dos limites não for informado, aquele lado não é restringido. |
| HU02-CA02 | Com um dia da semana, pegar só as respostas daquele dia, inclusive de semanas diferentes. Segunda = 0 até domingo = 6. |
| HU02-CA03 | Combinar os filtros. Para 19h às 20h na TV1, aceitar respostas da TV1 a partir de 19:00:00 e antes de 20:00:00, desde que também atendam ao período e ao dia da semana. |
| HU02-CA04 | Devolver lista vazia quando nada corresponder. Dar `ValueError` para início maior ou igual ao fim, dia fora de 0 a 6 e faixa de horário que não siga `0 <= hora_inicio < hora_fim <= 24` com inteiros, mesmo com a lista vazia. |

Nesta versão não dá para usar uma faixa que passa da meia-noite. Sem filtro nenhum, vêm todas as respostas.

### HU03 - Calcular aceitação e preferências

**Como gerente do Garage Burger, quero ver a média, a aceitação e as preferências de cada conteúdo, para saber o que agradou e o que os clientes gostariam de ver.**

| Critério | Condição verificável |
| --- | --- |
| HU03-CA01 | Para cada conteúdo exibido, devolver a quantidade de avaliações e a média das notas, além do total de respostas analisadas, sem misturar conteúdos. |
| HU03-CA02 | Calcular a aceitação pelas notas 4 ou 5. Com notas 1, 2, 3, 4 e 5 para o mesmo conteúdo, a aceitação é 40%. |
| HU03-CA03 | Contar as preferências separado do conteúdo exibido, sem mexer nas médias. Preferência vazia não conta voto, e preferência por um conteúdo que nunca passou também aparece na contagem. |
| HU03-CA04 | Sem avaliações, devolver total zero, nenhum conteúdo e nenhuma preferência, sem dividir por zero. |

### HU04 - Recomendar o conteúdo

**Como gerente do Garage Burger, quero receber uma recomendação de conteúdo para o recorte que escolhi, para montar a programação com base nas avaliações.**

| Critério | Condição verificável |
| --- | --- |
| HU04-CA01 | Com o mínimo padrão de 5, só entram no ranking conteúdos com 5 ou mais avaliações. O primeiro do ranking é o recomendado, com status `recomendado`. Um conteúdo com 4 avaliações não pode ganhar, mesmo com 100% de aceitação. |
| HU04-CA02 | Ordenar por aceitação (maior primeiro); empatou, por votos de preferência (mais primeiro); empatou de novo, por nome em ordem alfabética. |
| HU04-CA03 | Se ninguém atingir o mínimo, devolver status `dados_insuficientes`, conteúdo `None`, ranking vazio e o mínimo usado. |
| HU04-CA04 | Aceitar outro mínimo, desde que seja inteiro positivo. Dar `ValueError` para zero, negativo, número quebrado, texto ou booleano. |

### HU05 - Exportar o resultado

**Como gerente do Garage Burger, quero exportar o resultado da análise e o ranking, para consultar depois e usar na hora de organizar a programação.**

| Critério | Condição verificável |
| --- | --- |
| HU05-CA01 | Gerar um JSON em UTF-8 com o total de avaliações, o resumo de todos os conteúdos, as preferências, o status, o conteúdo escolhido, o mínimo usado e a ordem do ranking. Números continuam números, e "sem escolha" vira `null`. |
| HU05-CA02 | Gerar um CSV em UTF-8, separado por `;`, com as colunas `posicao`, `conteudo`, `qtd_avaliacoes`, `nota_media`, `taxa_aceitacao` e `votos_preferencia`, só com os conteúdos do ranking, na ordem dele, começando na posição 1. Os números usam ponto decimal. |
| HU05-CA03 | Se algum dos dois arquivos de destino já existir, dar `FileExistsError` antes de escrever qualquer coisa, sem apagar o que já estava lá e sem criar o outro. |
| HU05-CA04 | Sem avaliações, gerar o JSON com total zero, listas vazias, status `dados_insuficientes`, escolha `null` e ranking vazio, e o CSV só com o cabeçalho. |

O JSON guarda todos os conteúdos, até os com poucas avaliações, para consulta. O ranking e o CSV têm só os que atingiram o mínimo. A pasta de destino precisa existir antes de exportar.

## 5. Testes e critérios

Os testes estão em `testesGarage.py`. O nome e a docstring de cada teste dizem a história e o critério que ele verifica. São 20 testes, um por critério. Alguns testam vários casos de uma vez com `subTest`.

| História | Critério | Teste |
| --- | --- | --- |
| HU01 | HU01-CA01 | `TestHU01Importacao.test_hu01_ca01_importa_e_normaliza_csv_valido` |
| HU01 | HU01-CA02 | `TestHU01Importacao.test_hu01_ca02_rejeita_arquivo_com_cabecalho_incompleto` |
| HU01 | HU01-CA03 | `TestHU01Importacao.test_hu01_ca03_informa_linha_invalida_e_preserva_as_validas` |
| HU01 | HU01-CA04 | `TestHU01Importacao.test_hu01_ca04_rejeita_id_repetido_sem_sobrescrever_primeiro` |
| HU02 | HU02-CA01 | `TestHU02Filtros.test_hu02_ca01_periodo_inclui_inicio_e_exclui_fim` |
| HU02 | HU02-CA02 | `TestHU02Filtros.test_hu02_ca02_filtra_dia_da_semana_em_datas_diferentes` |
| HU02 | HU02-CA03 | `TestHU02Filtros.test_hu02_ca03_combina_periodo_dia_horario_e_tv` |
| HU02 | HU02-CA04 | `TestHU02Filtros.test_hu02_ca04_trata_vazio_e_rejeita_parametros_invalidos` |
| HU03 | HU03-CA01 | `TestHU03Indicadores.test_hu03_ca01_calcula_quantidade_e_media_por_conteudo` |
| HU03 | HU03-CA02 | `TestHU03Indicadores.test_hu03_ca02_aceitacao_considera_apenas_notas_quatro_e_cinco` |
| HU03 | HU03-CA03 | `TestHU03Indicadores.test_hu03_ca03_conta_preferencias_separadamente_das_notas` |
| HU03 | HU03-CA04 | `TestHU03Indicadores.test_hu03_ca04_sem_avaliacoes_nao_inventa_notas_ou_grupos` |
| HU04 | HU04-CA01 | `TestHU04Recomendacao.test_hu04_ca01_exige_amostra_minima_inclusiva` |
| HU04 | HU04-CA02 | `TestHU04Recomendacao.test_hu04_ca02_ordena_por_aceitacao_preferencia_e_nome` |
| HU04 | HU04-CA03 | `TestHU04Recomendacao.test_hu04_ca03_informa_dados_insuficientes_sem_escolha` |
| HU04 | HU04-CA04 | `TestHU04Recomendacao.test_hu04_ca04_minimo_configuravel_deve_ser_inteiro_positivo` |
| HU05 | HU05-CA01 | `TestHU05Exportacao.test_hu05_ca01_exporta_json_com_indicadores_e_recomendacao` |
| HU05 | HU05-CA02 | `TestHU05Exportacao.test_hu05_ca02_exporta_csv_na_ordem_do_ranking` |
| HU05 | HU05-CA03 | `TestHU05Exportacao.test_hu05_ca03_nao_sobrescreve_destinos_existentes` |
| HU05 | HU05-CA04 | `TestHU05Exportacao.test_hu05_ca04_exporta_resultado_vazio_sem_inventar_ranking` |

## 6. Funções do `garage.py`

| Função | O que faz | Devolve |
| --- | --- | --- |
| `importar_avaliacoes` | Lê, normaliza e valida o CSV. | `ResultadoImportacao` (respostas válidas e erros por linha) |
| `filtrar_avaliacoes` | Aplica o recorte escolhido. | Lista de `Avaliacao` |
| `calcular_indicadores` | Calcula médias, aceitação e preferências. | `Indicadores` |
| `gerar_recomendacao` | Aplica o mínimo e ordena o ranking. | `Recomendacao` |
| `exportar_relatorio` | Grava o JSON e o CSV. | Nada; os arquivos são a saída |

O fluxo é: importar, filtrar, calcular, recomendar e exportar. Para analisar outra TV ou outro horário, é só rodar de novo com outros filtros e outros nomes de saída.

## 7. Como rodar os testes

Precisa de **Python 3.10 ou mais novo**. Só usa a biblioteca padrão (`unittest`), não precisa instalar nada.

Na raiz do repositório:

```bash
python -m unittest -v testesGarage
```

(ou `python3 -m unittest -v testesGarage`, dependendo do computador)

Para rodar só uma história:

```bash
python -m unittest -v testesGarage.TestHU04Recomendacao
```

**Agora (Sprint 2):** os testes rodam e falham com `NotImplementedError`, porque as funções ainda não existem. Aparecem mais de 20 erros porque alguns testes verificam vários casos.

**Sprint 3:** depois de implementar, os mesmos 20 testes têm que passar.

## 8. Exemplo para conferir na Sprint 3

O CSV de exemplo (inventado) tem 15 respostas da TV1 em 30/10/2026, entre 18h e 20h. Sem filtro, o resultado esperado é:

| Conteúdo | Avaliações | Média | Aceitação | Preferências |
| --- | ---: | ---: | ---: | ---: |
| pop | 5 | 4,2 | 80% | 8 |
| rock | 5 | 3,6 | 60% | 3 |
| futebol | 5 | 3,0 | 40% | 4 |

Com mínimo de 5, recomenda `pop`, depois `rock` e `futebol`.

## 9. Arquivos da sprint

| Arquivo | Conteúdo |
| --- | --- |
| `Documentos/Sprint_2.md` | Este documento |
| `garage.py` | Estruturas e funções, ainda sem implementação |
| `testesGarage.py` | Os 20 testes |
| `dados/exemplo_avaliacoes_simuladas.csv` | Exemplo inventado para desenvolver e demonstrar |
| `README.md` | Links para os arquivos e como rodar |