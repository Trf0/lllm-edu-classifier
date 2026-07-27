# Classificador de Habilidades por Questão (LM Studio + Google Sheets)

## Sobre o projeto

Este projeto foi desenvolvido com o objetivo de automatizar a identificação
das habilidades cognitivas necessárias para responder questões de
plataformas de gamificação educacional, utilizando modelos de linguagem
(LLMs) integrados a ferramentas amplamente utilizadas no ambiente
acadêmico, como Google Sheets e Power BI.

A motivação surgiu a partir de entrevistas realizadas com professores e
profissionais da educação, nas quais foram identificados desafios
recorrentes relacionados ao tempo gasto na análise de questões, na
elaboração de intervenções pedagógicas e no acompanhamento do
desenvolvimento dos alunos. A classificação manual das habilidades
exigidas por cada questão é uma tarefa repetitiva, demorada e sujeita à
subjetividade, dificultando a utilização desses dados para apoiar
decisões pedagógicas.

Para enfrentar esse problema, foi desenvolvida uma solução em Python capaz
de integrar planilhas do Google Sheets a diferentes modelos de
Inteligência Artificial, tanto locais quanto baseados em APIs. A
aplicação envia automaticamente as questões para um modelo de linguagem,
que determina se determinada habilidade é necessária para resolvê-las. Os
resultados são armazenados de forma estruturada, permitindo posterior
análise em ferramentas de Business Intelligence, como o Power BI.

Além da implementação da solução, o projeto também avaliou diferentes
modelos de IA quanto ao tempo de processamento, qualidade das respostas,
ocorrência de alucinações e custo de execução. Foram realizados testes
experimentais utilizando métricas clássicas de classificação, como
precisão e recall, permitindo comparar diferentes abordagens e identificar
oportunidades de melhoria.

Um dos principais diferenciais do projeto é a possibilidade de execução
totalmente local através do LM Studio, reduzindo custos operacionais e
preservando a privacidade dos dados, aspecto especialmente relevante
quando se trabalha com informações educacionais. A arquitetura também
permite a substituição do modelo utilizado, possibilitando a comparação
entre modelos locais e serviços comerciais como OpenAI.

Embora tenha sido concebido para aplicações na área educacional, a
arquitetura desenvolvida é genérica e pode ser adaptada para outros
problemas de classificação automática de texto, análise documental ou
apoio à tomada de decisão baseada em Inteligência Artificial.

Este repositório reúne o código-fonte, a documentação, exemplos de
utilização e instruções para reprodução do ambiente de execução,
permitindo que outros pesquisadores, estudantes e desenvolvedores
utilizem, estudem ou expandam a solução.

Script que lê uma planilha do Google Sheets contendo perguntas de um quiz e
uma lista de habilidades, e usa um modelo de linguagem rodando **localmente
no LM Studio** para classificar, para cada par (pergunta, habilidade), se o
conhecimento daquela habilidade é necessário para responder à pergunta.
O resultado (0 ou 1) é escrito de volta na própria planilha, e uma fórmula
de porcentagem é atualizada em uma aba auxiliar a cada linha processada.

## Como funciona

1. Conecta na planilha do Google Sheets via uma conta de serviço (service
   account) do Google Cloud.
2. Lê todas as células já preenchidas.
3. Para cada célula ainda não classificada (diferente de "0" ou "1"):
   - Monta uma pergunta para o modelo local, perguntando se a habilidade da
     coluna é necessária para responder à pergunta da linha.
   - Envia essa pergunta ao LM Studio (endpoint compatível com a API da
     OpenAI) e espera uma resposta "0" ou "1".
   - Se a primeira resposta for "1", o modelo é consultado uma segunda vez
     para confirmar; só grava "1" se as duas respostas baterem.
4. Ao final de cada linha, atualiza a fórmula de porcentagem na aba
   "Porcentagem".

## Pré-requisitos

- Python 3.9+
- [LM Studio](https://lmstudio.ai/) instalado, com um modelo carregado e o
  **servidor local ligado** (aba "Local Server" do LM Studio, geralmente em
  `http://localhost:1234`).
- Uma conta de serviço do Google Cloud com acesso à planilha (ver abaixo).

## Instalação

```bash
git clone <url-do-seu-repositorio>
cd <pasta-do-repositorio>
python -m venv .venv
source .venv/bin/activate  # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuração

### 1. LM Studio

1. Abra o LM Studio.
2. Carregue o modelo que deseja usar (ex.: `qwen/qwen3-1.7b`).
3. Vá na aba de servidor local ("Local Server" / "Developer") e clique em
   **Start Server**.
4. Confira a porta exibida (por padrão `1234`). O script usa
   `http://localhost:1234/v1/chat/completions`.

### 2. Conta de serviço do Google

1. No [Google Cloud Console](https://console.cloud.google.com/), crie (ou
   use) um projeto e ative as APIs **Google Sheets API** e **Google Drive
   API**.
2. Crie uma conta de serviço e gere uma chave no formato JSON.
3. Compartilhe a planilha do Google Sheets com o e-mail da conta de serviço
   (o campo `client_email` dentro do JSON), dando permissão de edição.
4. Salve o arquivo JSON baixado em algum lugar do seu computador — **fora
   do repositório git**.

> ⚠️ **Nunca versione o arquivo JSON da conta de serviço.** Ele contém uma
> chave privada com acesso à sua conta Google. O `.gitignore` deste projeto
> já está configurado para ignorar arquivos `.json`.

### 3. Variáveis de ambiente

Copie o arquivo de exemplo e ajuste os valores:

```bash
cp .env.example .env
```

Edite o `.env`:

```
LM_STUDIO_URL=http://localhost:1234/v1/chat/completions
LM_STUDIO_MODEL=qwen/qwen3-1.7b
GOOGLE_CREDENTIALS_PATH=/caminho/completo/para/seu-arquivo.json
NOME_PLANILHA=Teste IA para classificações
ABA_PRINCIPAL=sheet1
ABA_PORCENTAGEM=Porcentagem
```

## Formato esperado da planilha

- **Aba principal**: a primeira linha (linha 1) contém os nomes das
  habilidades a partir da coluna C; a coluna B contém o texto de cada
  pergunta a partir da linha 3; as células internas (linha ≥ 3, coluna ≥ C)
  são preenchidas com "0"/"1" pelo script.
- **Aba "Porcentagem"**: precisa existir na mesma planilha; a célula C2
  recebe a fórmula de cálculo de porcentagem (a fórmula em si já é gerada
  pelo próprio código, na função `montar_formula_porcentagem` — não é
  preciso criá-la manualmente).

Um exemplo anonimizado da estrutura de planilha esperada (abas, colunas de
habilidades, formato de perguntas etc.) está em
`exemplos/exemplo_planilha.xlsx`.

## Rodando

```bash
python letramento_classificador.py
```

O script imprime no terminal, linha a linha, cada célula classificada
(`Linha X, Coluna Y: 0` ou `1`). Se a planilha já estiver totalmente
preenchida, ele apenas informa "Planilha já preenchida" e encerra.

## Estrutura do código

Todo o código está em `letramento_classificador.py`, organizado em
funções pequenas e independentes:

| Função | Responsabilidade |
|---|---|
| `numero_para_coluna` | Converte índice numérico em letra de coluna (A, B, ..., AA...) |
| `autenticar_google` | Autentica com a conta de serviço e devolve o cliente `gspread` |
| `abrir_planilhas` | Abre a planilha e devolve as duas abas usadas |
| `carregar_tabela` | Lê os valores da aba principal |
| `planilha_ja_preenchida` | Verifica se a planilha já foi totalmente classificada |
| `montar_payload` | Monta o corpo da requisição enviada ao LM Studio |
| `consultar_llm` | Faz uma chamada HTTP ao LM Studio |
| `consultar_llm_validado` | Repete a chamada até obter uma resposta "0"/"1" válida |
| `classificar_celula` | Aplica a lógica de dupla checagem para decidir 0 ou 1 |
| `montar_formula_porcentagem` | Monta a fórmula `ARRAYFORMULA` da aba "Porcentagem" |
| `processar_planilha` | Laço principal que percorre a tabela e atualiza a planilha |
| `main` | Ponto de entrada do script |

A lógica é exatamente a mesma da versão original — apenas foi separada em
funções e a configuração passou a vir de variáveis de ambiente em vez de
estar fixa no código.

## Dashboard (Power BI)

Este repositório também inclui o protótipo do dashboard usado para exibir os
resultados, em `dashboard/letramento_digital.pbix`. Para abri-lo é
necessário o [Power BI Desktop](https://powerbi.microsoft.com/desktop/)
(Windows). Ele contém as páginas:

- **Inicial** — navegação
- **Acompanhamento** — proficiência nas habilidades (com filtros)
- **Acompanhamento geral** — um gráfico por matéria (Português, Matemática,
  História, Inglês, Geografia, Ciências, Ed. Física, Artes)
- **Acompanhamento da sala** — proficiência filtrada por turma
- **Leaderboards** — ranking
- **Relações de habilidades**
- **Questões mais difíceis**

O dashboard lê da mesma planilha do Google Sheets que o script
`letramento_classificador.py` preenche.

## Observações

- O script depende de o LM Studio estar rodando e acessível na URL
  configurada antes de executar `python letramento_classificador.py`.
- Como o script chama o modelo local célula por célula (e até duas vezes
  por célula quando a primeira resposta é "1"), planilhas grandes podem
  levar bastante tempo para serem totalmente processadas.
