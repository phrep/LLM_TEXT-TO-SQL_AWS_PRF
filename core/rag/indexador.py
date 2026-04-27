from langchain_qdrant import QdrantVectorStore
from langchain_aws import BedrockEmbeddings
from dotenv import load_dotenv
import os

from core.rag.loader import criar_documentos_schema

load_dotenv()


# =========================
# EMBEDDING — AWS Bedrock Titan
# =========================
def get_embedding():

    return BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=os.getenv("AWS_REGION", "xxx"),
    )


# =========================
# INDEXAÇÃO
# =========================
def indexar_documentos(nome_colecao: str, docs: list):
    QdrantVectorStore.from_documents(
        documents=docs,
        embedding=get_embedding(),
        url=os.getenv("QDRANT_URL", "http://localhost:xxx"),
        collection_name=nome_colecao,
    )


# =========================
# CONEXÃO COM QDRANT
# =========================
def banco_qdrant(nome_colecao: str) -> QdrantVectorStore:
    return QdrantVectorStore.from_existing_collection(
        collection_name=nome_colecao,
        url=os.getenv("QDRANT_URL", "http://localhost:xx"),
        embedding=get_embedding(),
    )


# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    documentos = criar_documentos_schema()
    indexar_documentos("prf_acidentes_schema", documentos)
    print("✅ Schema indexado no Qdrant com sucesso!")