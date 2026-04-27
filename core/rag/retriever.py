from dotenv import load_dotenv
load_dotenv()

from operator import itemgetter
import re
import os
import pandas as pd
from functools import lru_cache

# from langchain_aws import ChatBedrock
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from core.rag.indexador import banco_qdrant
from infrastructure.database.connection import conn


# =========================
# LIMPAR SQL
# =========================
def limpar_sql(resposta: str) -> str:
    resposta = resposta.strip()
    resposta = re.sub(r"```sql|```", "", resposta)
    return resposta.strip()


# =========================
# VALIDAR SQL (SEGURANÇA)
# =========================
def validar_sql(sql: str):
    sql_upper = sql.upper()
    palavras_proibidas = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]
    for palavra in palavras_proibidas:
        if palavra in sql_upper:
            raise ValueError(f"❌ Query não permitida: contém '{palavra}'")
    if "SELECT" not in sql_upper:
        raise ValueError("❌ Apenas queries SELECT são permitidas")
    return True


# =========================
# LIMITADOR DE QUERY 
# =========================
def garantir_limit(sql: str, limite: int = 100) -> str:
    if "LIMIT" not in sql.upper():
        sql += f" LIMIT {limite}"
    return sql


# =========================
# EXECUTAR ATHENA (COM CACHE)
# =========================
@lru_cache(maxsize=50)
def executar_sql_cache(sql: str) -> pd.DataFrame:
    print("⚡ Executando no Athena...")
    return pd.read_sql(sql, conn)


# =========================
# FORMATAR CONTEXTO
# =========================
def cria_texto(documentos) -> str:
    return "\n\n".join(doc.page_content for doc in documentos)


# =========================
# QDRANT — inicializado via env var
# =========================
db = banco_qdrant("prf_acidentes_schema")


def buscar_contexto(pergunta: str) -> str:
    docs = db.similarity_search(pergunta, k=10)

    colunas   = [d for d in docs if d.metadata.get("type") == "column"][:4]
    regras    = [d for d in docs if d.metadata.get("type") == "rule"][:2]
    exemplos  = [d for d in docs if d.metadata.get("type") == "sql_example"][:2]
    metricas  = [d for d in docs if d.metadata.get("type") == "metric"][:1]

    return cria_texto(colunas + regras + exemplos + metricas)


# =========================
# PROMPT
# =========================
SYSTEM_PROMPT = """
Você é especialista em SQL para AWS Athena.

Use APENAS a tabela:
"tabela_prf_all_acidentes_db"."acidentes"

Contexto:
{contexto}

Regras obrigatórias:
- Use exatamente os nomes das colunas do contexto
- Para contagem use COUNT(*)
- Para mortos/feridos use CAST(campo AS INTEGER)
- Sempre use GROUP BY quando houver agregação
- Sempre filtre por ano ou uf quando fizer sentido
- Nunca invente colunas ou tabelas
- Nomes de municípios sempre em MAIÚSCULAS sem acentos
- Nomes de UF sempre em MAIÚSCULAS

Formato da resposta:
- Retorne apenas SQL válido
- Sem explicações
- Sem texto adicional
"""

prompt_template = ChatPromptTemplate([
    ("system", SYSTEM_PROMPT),
    ("human", "{pergunta}"),
])


model = ChatBedrockConverse(
    model=os.getenv("BEDROCK_LLM_MODEL", "amazon.nova-lite-v1:0"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

chain = (
    RunnableParallel({
        "pergunta": itemgetter("pergunta"),
        "contexto": itemgetter("pergunta") | RunnableLambda(buscar_contexto),
    })
    | prompt_template
    | model
    | StrOutputParser()
)


# =========================
# FUNÇÃO PRINCIPAL
# =========================
def gerar_sql_e_consultar(pergunta: str):
    try:
        print("\n🧠 Pergunta:", pergunta)

        resposta_llm = chain.invoke({"pergunta": pergunta})
        sql = limpar_sql(resposta_llm)
        print("\n📜 SQL gerado:\n", sql)

        validar_sql(sql)
        sql = garantir_limit(sql)
        print("\n🚀 SQL final (com LIMIT):\n", sql)

        df = executar_sql_cache(sql)
        return sql, df

    except Exception as e:
        print("❌ Erro:", e)
        raise  # re-raise para o Streamlit capturar e exibir corretamente