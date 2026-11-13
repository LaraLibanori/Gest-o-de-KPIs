# Roteiro de avaliação de usabilidade

Protocolo pronto para aplicar com participantes reais e preencher os campos
amarelos da Entrega Final (usabilidade, N de participantes, valores da
plataforma). Eu não posso recrutar ou conduzir sessões com pessoas — isso só
você (Lara) consegue fazer. O que este documento entrega é o instrumento
inteiro, já no formato que o referencial do TCC usa (ISO 9241-11, Nielsen,
SUS), para aplicar e depois só colar os números no texto.

Referencial coberto: ISO 9241-11:2018 (eficácia, eficiência, satisfação),
Nielsen 1993 / Nielsen-Landauer 1993 (tamanho da amostra), SUS — System
Usability Scale (Brooke 1996, tradução validada por Martins et al. 2015 para
português do Brasil).

## 1. Quantos participantes

Nielsen (1993) mostra que 5 participantes já revelam ~85% dos problemas de
usabilidade de uma interface; acima de 8 o retorno marginal cai muito para o
custo de recrutar mais gente. Para o TCC, **5 a 8 participantes** é uma
amostra defensável e citável. Procure variar o perfil: pelo menos uma pessoa
que já usa ferramentas de BI (Power BI, Looker, planilhas complexas) e pelo
menos uma que não usa, para o SUS não medir só "achei fácil porque já
conheço o gênero de ferramenta".

## 2. Antes da sessão

Leia para o participante (ou mande por escrito e peça para confirmar que
leu):

> Vamos testar uma plataforma de dashboards de indicadores. Não existe
> resposta certa ou errada — quem está sendo avaliado é a plataforma, não
> você. Pense alto enquanto tenta as tarefas: o que está procurando, o que
> achou confuso, o que esperava que acontecesse. Posso anotar o tempo e
> onde você clica, só para o trabalho de conclusão de curso. Pode parar a
> qualquer momento.

Dados a registrar por participante: perfil (usa ferramenta de BI? sim/não),
hora de início de cada tarefa, hora de término, se concluiu sem ajuda, se
pediu ajuda (e em qual ponto), e qualquer comentário espontâneo.

## 3. Tarefas (use a conta de demonstração ou uma conta nova)

| # | Tarefa | O que conta como sucesso | Métrica (ISO 9241-11) |
|---|---|---|---|
| 1 | Criar uma conta e entrar na plataforma | Chega à tela inicial logado, sem ajuda | Eficácia (concluiu?), eficiência (tempo) |
| 2 | Cadastrar uma conexão usando a base de exemplo (`make exemplo`), do início ao fim do assistente | Conexão aparece com etapa "pronta" | Eficácia, eficiência |
| 3 | Confirmar o catálogo de campos sugerido pela plataforma | Catálogo confirmado, sem reverter nenhuma sugestão por engano | Eficácia, eficiência |
| 4 | Criar um indicador novo (ex.: "Ticket médio") e definir uma meta para ele | Indicador aparece no painel com a meta e o sinal (atingiu/perto/abaixo) | Eficácia, eficiência |
| 5 | Trocar o tipo de gráfico de um indicador existente | Gráfico muda sem precisar recarregar a página manualmente | Eficácia |
| 6 | Montar um dashboard juntando 2 indicadores de conexões diferentes (se houver mais de uma conexão) ou da mesma conexão | Dashboard criado e visível na lista | Eficácia, eficiência |
| 7 | Encontrar "o que mudou" em um indicador no último período | Localiza a explicação sem pedir ajuda | Eficácia |

Para cada tarefa, registre: concluiu sim/não, tempo em segundos, número de
cliques/tentativas erradas, e se pediu ajuda.

## 4. Depois da sessão: questionário SUS

Leia cada frase e peça uma nota de 1 (discordo totalmente) a 5 (concordo
totalmente). É a tradução validada para português do Brasil — não reordene
nem reformule as frases, isso invalidaria a pontuação padronizada.

1. Eu acho que gostaria de usar este site/sistema frequentemente.
2. Eu achei este site/sistema complexo sem necessidade.
3. Eu achei este site/sistema fácil de usar.
4. Eu acho que precisaria de ajuda de uma pessoa com conhecimentos técnicos
   para conseguir utilizar este site/sistema.
5. Eu achei que as várias funções deste site/sistema estavam bem integradas.
6. Eu achei que houve muita inconsistência neste site/sistema.
7. Eu imagino que a maioria das pessoas aprenderia a usar este site/sistema
   rapidamente.
8. Eu achei este site/sistema muito complicado de usar.
9. Eu me senti muito confiante usando este site/sistema.
10. Eu precisei aprender muitas coisas novas antes de conseguir utilizar
    este site/sistema.

### Como calcular a pontuação SUS (0 a 100)

Para as perguntas ímpares (1, 3, 5, 7, 9): pontuação = nota dada − 1.
Para as perguntas pares (2, 4, 6, 8, 10): pontuação = 5 − nota dada.
Some as 10 pontuações (vai de 0 a 40) e multiplique por 2,5 → SUS de 0 a 100.

Faça isso por participante, depois tire a média das notas SUS de todos os
participantes — é esse número médio que entra no texto do TCC. Referência
de leitura (Bangor, Kortum & Miller 2009, citável se quiser contextualizar
a nota): acima de 68 é considerado "acima da média"; 80+ é considerado bom.

## 5. Três perguntas abertas, ao final

1. O que você achou mais fácil na plataforma?
2. O que você achou mais difícil ou confuso?
3. Teria algo que você esperava encontrar e não encontrou?

As respostas aqui são o material para a seção qualitativa do capítulo de
avaliação — cite 2 ou 3 falas literais (entre aspas, com o participante
anonimizado como "P1", "P2"...) como evidência.

## 6. Planilha de coleta

Monte uma planilha (Google Sheets ou Excel) com uma linha por participante e
estas colunas: `participante`, `usa_bi` (sim/não), depois, para cada tarefa
1 a 7: `concluiu_1`, `tempo_1_s`, `ajuda_1`, ..., depois `sus_1` a `sus_10`
(as notas brutas de 1 a 5) e por fim `sus_pontuacao` (já calculada pela
fórmula acima). Isso dá, direto, a taxa de sucesso por tarefa (% que
concluiu), o tempo médio por tarefa e a nota SUS média — os três números que
a Entrega Final pede.

## 7. O que vai para o texto do TCC

- N de participantes e perfil (quantos usam BI, quantos não usam).
- Taxa de sucesso por tarefa (ex.: "6 de 7 tarefas tiveram 100% de conclusão
  sem ajuda; a tarefa 4 teve 1 participante pedindo ajuda para encontrar o
  campo de meta").
- Tempo médio por tarefa, se achar relevante destacar algum extremo (uma
  tarefa muito rápida ou muito lenta).
- Nota SUS média, com a leitura de Bangor et al. (acima/abaixo de 68).
- 2-3 citações literais das perguntas abertas, como evidência qualitativa.
