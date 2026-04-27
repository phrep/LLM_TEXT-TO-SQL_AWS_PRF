from qdrant_client import QdrantClient

client = QdrantClient(url="xxxxxx")

client.delete_collection("prf_acidentes_schema")

print("Collection deletada com sucesso!")