# 📊 Data Copilot PRF — Text-to-SQL com RAG na AWS

> Interface conversacional sobre dados reais da PRF. O usuário faz uma pergunta em linguagem natural e recebe o SQL gerado, a tabela de resultados e um gráfico — sem conhecimento técnico necessário.

---

## 🏗️ Arquitetura

```
Usuário
   │ pergunta em linguagem natural
   ▼
ECS — Streamlit App (ECR image)
   ├── Qdrant (EC2) ──── busca vetorial do schema
   ├── AWS Bedrock ───── Titan Embed v2 + Nova Lite LLM
   └── Athena ────────── executa SQL gerado
            │
           S3 ─── Data lake Parquet particionado por ano/UF
```

---

## 🛠️ Stack

| Camada | Tecnologia |
|---|---|
| Interface | Streamlit + Docker |
| Orquestração LLM | LangChain (RunnableParallel, RAG, ChatPromptTemplate) |
| Embedding | AWS Bedrock — Amazon Titan Embed Text v2 (1024d) |
| LLM | AWS Bedrock — Amazon Nova Lite |
| Banco vetorial | Qdrant (EC2 dedicado) |
| Data lake | S3 + Parquet + particionamento por ano/UF |
| Query engine | AWS Athena (serverless) |
| Container registry | Amazon ECR |
| Runtime | Amazon ECS (Fargate) |
| Observabilidade | AWS CloudWatch |
| Autenticação | IAM Role (zero chaves hardcoded) |

---

## 📁 Estrutura do projeto

```
projeto/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── app/
│   └── main.py              # Interface Streamlit
└── core/
    └── rag/
        ├── loader.py                # Documentos de schema para indexação
        ├── indexador.py             # Indexação no Qdrant via Bedrock Embeddings
        └── retriever.py             # Chain LangChain: RAG + LLM + SQL
        └── delete_collection.py     # Deleta collection Qdrant se for preciso
    infrastructure/
    └── database/
        └── connection.py    # Conexão Athena (local + ECS IAM Role)
```

---

## ⚙️ Como rodar localmente

### Pré-requisitos
- Docker Desktop
- Credenciais AWS com acesso ao Bedrock e Athena
- Acesso habilitado aos modelos: `amazon.titan-embed-text-v2:0` e `amazon.nova-lite-v1:0`

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env com suas credenciais
```

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
AWS_REGION=us-east-1
S3_STAGING_DIR=s3://seu-bucket/athena-results/
ATHENA_DATABASE=seu_database
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_LLM_MODEL=amazon.nova-lite-v1:0
QDRANT_URL=http://localhost:xxxx
QDRANT_API_KEY=
QDRANT_COLLECTION=prf_acidentes_schema
QUERY_LIMIT=100
```

### 2. Subir os containers

```bash
docker compose up --build -d
```

### 3. Indexar o schema no Qdrant (apenas na primeira vez)

```bash
docker compose exec app python -m core.rag.indexador
```

### 4. Acessar

```
http://localhost:xxx
```

---

## 🚀 Deploy na AWS

### Build e push para o ECR

```bash
# Login
aws ecr get-login-password --region us-xxxxx | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-xxxxx.amazonaws.com

# Tag e push
docker tag aws_prf_llm_final-app:latest \
  <ACCOUNT_ID>.dkr.ecr.us-xxxxx.amazonaws.com/data-copilot-prf:latest

docker push \
  <ACCOUNT_ID>.dkr.ecr.us-xxxxx.amazonaws.com/data-copilot-prf:latest
```

### Indexar no Qdrant do EC2

```bash
docker run --rm --env-file .env \
  -e QDRANT_URL=http://<IP_EC2>:6333 \
  aws_prf_llm_final-app \
  python -m core.rag.indexador
```

### Atualizar o serviço ECS

```bash
aws ecs update-service \
  --cluster xxxx\
  --service xxx \
  --force-new-deployment \
  --region xxxx
```

### Variáveis de ambiente na Task Definition

```
QDRANT_URL          = http://<IP_PRIVADO_EC2>:6333
QDRANT_COLLECTION   = xxxxx
ATHENA_DATABASE     = tabela_xxxx
S3_STAGING_DIR      = s3://cons-athena/athena-results/
AWS_REGION          = xxxx
AWS_DEFAULT_REGION  = xxxx
BEDROCK_LLM_MODEL   = amazon.nova-lite-v1:0
BEDROCK_EMBED_MODEL = amazon.titan-embed-text-v2:0
QUERY_LIMIT         = 100
```

> Em produção **não** inclua AWS_ACCESS_KEY_ID nem AWS_SECRET_ACCESS_KEY — a IAM Role da task resolve automaticamente.

---

## 🔐 IAM Role — permissões mínimas

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "athena:StartQueryExecution",
    "athena:GetQueryExecution",
    "athena:GetQueryResults",
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": "*"
}
```

---

## 🧠 Como o RAG funciona aqui

O schema da tabela Athena é indexado como documentos vetoriais individuais no Qdrant:

| Tipo | Conteúdo | Qtd |
|---|---|---|
| `column` | Nome exato, descrição e instrução de uso de cada coluna | 29 |
| `rule` | CAST de tipos, filtros de partição, maiúsculas em municípios | 3 |
| `sql_example` | Queries completas para casos de uso comuns | 4 |
| `metric` | Padrões de COUNT e SUM | 1 |

Quando o usuário pergunta, o sistema recupera os 10 documentos mais similares e filtra por tipo antes de montar o prompt — garantindo contexto preciso sem ruído.

---

## 💡 Decisões técnicas relevantes

**HuggingFace → Bedrock:** O modelo multilíngue local causava OOM no ECS (400–900MB só para carregar). Migração para Titan Embed via Bedrock eliminou o problema — embedding como API, pay-per-token, sem modelo em memória.

**EC2 dedicado para Qdrant:** Qdrant é stateful. No ECS, cada deploy destruiria a collection. No EC2 com EBS separado, o banco vetorial tem ciclo de vida independente da aplicação.

**Segurança:** Zero chaves hardcoded. Em produção a IAM Role da task ECS resolve autenticação com Bedrock, Athena e S3 automaticamente.

## 🚀 Próximos passos

- 🔍 **Análise em linguagem natural (LLM Insights)**  
  Gerar explicações automáticas sobre os resultados retornados pelo SQL  
  (ex: tendências, padrões e insights relevantes para o negócio)

- ⚡ **Cache de consultas com Redis / Valkey**  
  Reduzir latência e custo em queries repetidas no Athena

- 🔁 **Pipeline CI/CD**  
  Automatizar build, testes e deploy da aplicação (Docker → ECR → ECS)


---

## 📊 Exemplos de perguntas

- `Ranking 10 causas de acidentes em SP decrescente`
- `Top 10 estados com mais acidentes por ano`
- `Quantos acidentes ocorreram por mês em 2025`
- `Total de mortes por estado`
- `Top 10 km com maior índice de acidentes em São José dos Campos`
