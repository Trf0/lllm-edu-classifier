"""
Classificador de habilidades por questão usando um LLM local (LM Studio).

O script lê uma planilha do Google Sheets com perguntas x habilidades,
pergunta a um modelo local (via LM Studio) se cada habilidade é
necessária para responder cada pergunta, e preenche a planilha com
0 ou 1. Ao final de cada linha processada, atualiza também uma célula
de fórmula (ARRAYFORMULA) na aba "Porcentagem".

A lógica é a mesma do script original; apenas foi dividida em funções
menores e a configuração (caminhos, nomes, URL do LM Studio) passou a
vir de variáveis de ambiente / arquivo .env, em vez de estar fixa no
código.
"""

import os
import time

import gspread
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# ---------------------------------------------------------------------------
# Configuração (lida de variáveis de ambiente / arquivo .env)
# ---------------------------------------------------------------------------

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
MODEL_NAME = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-1.7b")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
NOME_PLANILHA = os.getenv("NOME_PLANILHA", "Teste IA para classificações")
ABA_PRINCIPAL = os.getenv("ABA_PRINCIPAL", "sheet1")
ABA_PORCENTAGEM = os.getenv("ABA_PORCENTAGEM", "Porcentagem")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ---------------------------------------------------------------------------
# Utilitário de conversão número -> letra de coluna (estilo Excel/Sheets)
# ---------------------------------------------------------------------------

def numero_para_coluna(n):
    """Converte um índice numérico (0-based) para a letra de coluna (A, B, ..., AA, ...)."""
    coluna = ""
    while n >= 0:
        coluna = chr((n % 26) + 65) + coluna
        n = n // 26 - 1
    return coluna


# ---------------------------------------------------------------------------
# Autenticação e acesso ao Google Sheets
# ---------------------------------------------------------------------------

def autenticar_google(credentials_path=GOOGLE_CREDENTIALS_PATH, scopes=SCOPES):
    """Autentica com a conta de serviço do Google e devolve o cliente gspread autorizado."""
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return gspread.authorize(creds)


def abrir_planilhas(client, nome_planilha=NOME_PLANILHA,
                     aba_principal=ABA_PRINCIPAL, aba_porcentagem=ABA_PORCENTAGEM):
    """Abre a planilha e devolve (aba principal, aba de porcentagem)."""
    arquivo = client.open(nome_planilha)
    sheet = arquivo.sheet1 if aba_principal == "sheet1" else arquivo.worksheet(aba_principal)
    sheet2 = arquivo.worksheet(aba_porcentagem)
    return sheet, sheet2


def carregar_tabela(sheet):
    """Lê todos os valores da aba principal e devolve (tabela, num_linhas, num_colunas)."""
    tabela = sheet.get_all_values()
    linhas_preenchidas = len(tabela)
    colunas_preenchidas = len(tabela[0]) if tabela else 0
    return tabela, linhas_preenchidas, colunas_preenchidas


def planilha_ja_preenchida(tabela, linhas_preenchidas, colunas_preenchidas):
    """Verifica se a última célula da tabela já foi classificada (0 ou 1)."""
    ultimo_valor = tabela[linhas_preenchidas - 1][colunas_preenchidas - 1]
    return ultimo_valor in ["0", "1"]


# ---------------------------------------------------------------------------
# Comunicação com o LM Studio
# ---------------------------------------------------------------------------

def montar_payload(pergunta, habilidade, model=MODEL_NAME):
    """Monta o payload enviado ao LM Studio para uma pergunta/habilidade específica."""
    return {
        "model": model,
        "temperature": 0.2,
        "top_p": 0.9,
        "top_k": 20,
        "min_p": 0.1,
        "repetition_penalty": 1.2,
        "messages": [
            {
                "role": "system",
                "content": """Responda apenas como 0 ou 1.

                sendo 0, não é necessário o conhecimento e 1 é necessário o conhhecimento e dá para resolver apenas se eu souber plenamente sobre, caso não haja certeza se é necessário a resposta é 0.

                Se a resposta pode ser 0, logo a resposta é 0.
                """,
            },
            {
                "role": "user",
                "content": f"Para a pergunta ({pergunta}) é necessário o conhecimento sobre ({habilidade})?",
            },
        ],
    }


def consultar_llm(url, payload):
    """Envia o payload ao LM Studio e devolve a resposta bruta (texto) do modelo."""
    res = requests.post(url, json=payload)
    data = res.json()
    return data["choices"][0]["message"]["content"].strip()


def consultar_llm_validado(url, payload):
    """Chama o LM Studio repetidamente até obter uma resposta válida ("0" ou "1")."""
    resposta = consultar_llm(url, payload)
    while resposta not in ["0", "1"]:
        resposta = consultar_llm(url, payload)
    return resposta


# ---------------------------------------------------------------------------
# Classificação de uma célula (pergunta x habilidade)
# ---------------------------------------------------------------------------

def classificar_celula(url, payload):
    """
    Roda a checagem em até duas passadas (para reduzir ruído do modelo):
    - Se a 1ª resposta for "0", classifica direto como "0".
    - Se a 1ª resposta for "1", roda uma 2ª vez; só confirma "1" se as duas
      baterem, senão cai para "0".
    """
    resposta1 = consultar_llm_validado(url, payload)

    if resposta1 == "1":
        resposta2 = consultar_llm_validado(url, payload)
        return "1" if resposta1 == resposta2 else "0"

    return "0"


# ---------------------------------------------------------------------------
# Fórmula de porcentagem (aba "Porcentagem")
# ---------------------------------------------------------------------------

def montar_formula_porcentagem(i, colunas_preenchidas):
    """Monta a fórmula ARRAYFORMULA usada na aba de porcentagem, para a linha i processada."""
    col_i = numero_para_coluna(i)
    col_ult = numero_para_coluna(colunas_preenchidas - 1)

    return f'''=ARRAYFORMULA(
    SE(
    MATRIZ.MULT(
    FILTER(
        FILTER(
          SE('Alunos/Acertos'!C2:{col_i}="";"";('Alunos/Acertos'!C2:{col_i}>0)*1);
          'Alunos/Acertos'!C2:{col_i}2<>""
        );
        'Alunos/Acertos'!A2:A<>""
      );
      FILTER(
        FILTER('Página1'!C3:ZZZ;'Página1'!ET3:ET<>"");
        'Página1'!C3:ZZZ3<>""
      )
    )=0;
    
    0;
    
    MATRIZ.MULT(
      FILTER(
        FILTER(
          SE('Alunos/Acertos'!C2:{col_i}="";"";('Alunos/Acertos'!C2:{col_i}=2)*1);
          'Alunos/Acertos'!C2:{col_i}2<>""
        );
        'Alunos/Acertos'!A2:A<>""
      );
      FILTER(
        FILTER('Página1'!C3:{col_ult};'Página1'!{col_ult}3:{col_ult}<>"");
        'Página1'!C3:{col_ult}3<>""
      )
    )
    /
    MATRIZ.MULT(
      FILTER(
        FILTER(
          SE('Alunos/Acertos'!C2:{col_i}="";"";('Alunos/Acertos'!C2:{col_i}>0)*1);
          'Alunos/Acertos'!C2:{col_i}2<>""
        );
        'Alunos/Acertos'!A2:A<>""
      );
      FILTER(
        FILTER('Página1'!C3:{col_ult};'Página1'!{col_ult}3:{col_ult}<>"");
        'Página1'!C3:{col_ult}3<>""
      )
    )
  )
)
        '''


# ---------------------------------------------------------------------------
# Processamento principal da planilha
# ---------------------------------------------------------------------------

def processar_planilha(sheet, sheet2, tabela, linhas_preenchidas, colunas_preenchidas, url=LM_STUDIO_URL):
    """Percorre a tabela, classifica cada célula pendente e atualiza a planilha."""
    for i in range(2, linhas_preenchidas):
        for j in range(2, colunas_preenchidas):
            valor = tabela[i][j]

            # só processa se a célula ainda não tiver 0 ou 1
            if valor not in ["0", "1"]:
                pergunta = tabela[i][1]
                habilidade = tabela[1][j]

                payload = montar_payload(pergunta, habilidade)
                resultado = classificar_celula(url, payload)

                sheet.update_cell(i + 1, j + 1, resultado)
                print(f"Linha {i}, Coluna {j}: {resultado}")

        sheet2.update_cell(2, 3, montar_formula_porcentagem(i, colunas_preenchidas))


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main():
    client = autenticar_google()
    sheet, sheet2 = abrir_planilhas(client)

    tabela, linhas_preenchidas, colunas_preenchidas = carregar_tabela(sheet)
    print(linhas_preenchidas, colunas_preenchidas)

    if planilha_ja_preenchida(tabela, linhas_preenchidas, colunas_preenchidas):
        print("Planilha já preenchida")
        return

    processar_planilha(sheet, sheet2, tabela, linhas_preenchidas, colunas_preenchidas)


if __name__ == "__main__":
    main()
