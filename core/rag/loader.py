import os
from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()

# =========================
# CONFIGURAÇÃO
# Permite trocar database entre ambientes (dev/prod) via .env
# =========================
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "tabela_prf_xxx")
TABLE_NAME      = f'"{ATHENA_DATABASE}"."acidentes"'


# =========================
# SCHEMA — definido antes de ser usado
# =========================
schema_docs = [
    {"column": "id",                       "desc": "Identificador único do acidente"},
    {"column": "data_inversa",             "desc": "Data do acidente"},
    {"column": "dia_semana",               "desc": "Dia da semana do acidente"},
    {"column": "horario",                  "desc": "Horário do acidente"},
    {"column": "br",                       "desc": "Rodovia BR onde ocorreu o acidente"},
    {"column": "km",                       "desc": "Quilômetro da rodovia onde ocorreu o acidente"},
    {"column": "municipio",               "desc": "Município onde ocorreu o acidente"},
    {"column": "causa_acidente",           "desc": "Descrição da causa do acidente"},
    {"column": "tipo_acidente",            "desc": "Tipo do acidente"},
    {"column": "classificacao_acidente",   "desc": "Gravidade do acidente"},
    {"column": "fase_dia",                 "desc": "Período do dia"},
    {"column": "condicao_metereologica",   "desc": "Condição climática"},
    {"column": "tipo_pista",               "desc": "Tipo da pista"},
    {"column": "uso_solo",                 "desc": "Uso do solo"},
    {"column": "tipo_veiculo",             "desc": "Tipo de veículo"},
    {"column": "marca",                    "desc": "Marca do veículo"},
    {"column": "idade",                    "desc": "Idade da pessoa"},
    {"column": "sexo",                     "desc": "Sexo da pessoa"},
    {"column": "ilesos",                   "desc": "Quantidade de ilesos (string numérica)"},
    {"column": "feridos_leves",            "desc": "Feridos leves (string numérica)"},
    {"column": "feridos_graves",           "desc": "Feridos graves (string numérica)"},
    {"column": "mortos",                   "desc": "Mortos (string numérica)"},
    {"column": "latitude",                 "desc": "Latitude"},
    {"column": "longitude",               "desc": "Longitude"},
    {"column": "regional",                 "desc": "Regional da PRF"},
    {"column": "delegacia",                "desc": "Delegacia"},
    {"column": "uop",                      "desc": "Unidade operacional"},
    {"column": "mes",                      "desc": "Mês"},
    {"column": "ano",                      "desc": "Ano (partição)"},
    {"column": "uf",                       "desc": "Estado (UF)"},
]


# =========================
# DOCUMENTOS PARA INDEXAÇÃO
# =========================
def criar_documentos_schema():
    documentos = []

    # --- Contexto geral da tabela ---
    documentos.append(Document(
        page_content=f"""
Tabela: {TABLE_NAME}

Descrição:
Tabela contendo registros de acidentes em rodovias federais do Brasil.

Use esta tabela para análises de:
- Quantidade de acidentes
- Análises por estado (uf)
- Análises por cidade (municipio)
- Análises temporais (ano, mes, dia_semana, horario)
- Causas e tipos de acidentes
- Condição climática (condicao_metereologica)
- Tipo de veículo
- Sexo e idade da pessoa envolvida
- Localização geográfica (latitude, longitude)
""",
        metadata={"type": "table_context"}
    ))

    # --- Uma entrada por coluna ---
    for col in schema_docs:
        documentos.append(Document(
            page_content=f"""
Coluna: {col['column']}
Descrição: {col['desc']}
Tabela: {TABLE_NAME}

Instruções:
- Use exatamente o nome da coluna: {col['column']}
- Esta coluna pertence à tabela {TABLE_NAME}
""",
            metadata={
                "type": "column",
                "column_name": col["column"],
                "table": TABLE_NAME,
            }
        ))

    # --- Métrica principal ---
    documentos.append(Document(
        page_content=f"""
Para calcular número de acidentes:

SELECT COUNT(*) FROM {TABLE_NAME}

Para agrupamentos:
SELECT coluna, COUNT(*) as total
FROM {TABLE_NAME}
GROUP BY coluna
ORDER BY total DESC
""",
        metadata={"type": "metric"}
    ))

    # --- Regras de negócio ---
    documentos.append(Document(
        page_content="""
As colunas mortos, feridos_leves, feridos_graves e ilesos são do tipo STRING.

Sempre converter antes de somar:
CAST(coluna AS INTEGER)

Exemplo:
SUM(CAST(mortos AS INTEGER))
""",
        metadata={"type": "rule"}
    ))

    documentos.append(Document(
        page_content="""
Sempre que possível, aplique filtros de partição para reduzir custo no Athena.

Priorize:
- filtro por ano  (coluna de partição)
- filtro por uf

Exemplo:
WHERE ano = 2025 AND uf = 'SP'
""",
        metadata={"type": "rule"}
    ))

    documentos.append(Document(
        page_content="""
Nomes de municípios e UF devem sempre estar em MAIÚSCULAS e SEM acentos nas queries SQL.

Exemplos corretos:
  municipio = 'SAO JOSE DOS CAMPOS'
  uf = 'SP'

Exemplos incorretos:
  municipio = 'São José dos Campos'
  uf = 'sp'
""",
        metadata={"type": "rule"}
    ))

    # --- Exemplos de SQL ---
    documentos.append(Document(
        page_content=f"""
Exemplo: quantidade de acidentes por estado

SELECT uf, COUNT(*) as total_acidentes
FROM {TABLE_NAME}
GROUP BY uf
ORDER BY total_acidentes DESC
""",
        metadata={"type": "sql_example"}
    ))

    documentos.append(Document(
        page_content=f"""
Exemplo: acidentes por ano

SELECT ano, COUNT(*) as total
FROM {TABLE_NAME}
GROUP BY ano
ORDER BY ano DESC
""",
        metadata={"type": "sql_example"}
    ))

    documentos.append(Document(
        page_content=f"""
Exemplo: total de mortos por estado

SELECT uf, SUM(CAST(mortos AS INTEGER)) as total_mortos
FROM {TABLE_NAME}
GROUP BY uf
ORDER BY total_mortos DESC
""",
        metadata={"type": "sql_example"}
    ))

    documentos.append(Document(
        page_content=f"""
Exemplo: top 10 causas de acidentes em SP

SELECT causa_acidente, COUNT(*) as total
FROM {TABLE_NAME}
WHERE uf = 'SP'
GROUP BY causa_acidente
ORDER BY total DESC
LIMIT 10
""",
        metadata={"type": "sql_example"}
    ))

    return documentos