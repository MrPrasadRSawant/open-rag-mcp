# Open RAG MCP Backend

FastAPI backend for Open RAG MCP.

## Local Setup

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e backend[dev]
copy .env.example .env
python -m run
```

The default vector store is ChromaDB, configured by:

```text
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIRECTORY=./data/chroma
CHROMA_COLLECTION_NAME=open_rag_documents
```

Set `VECTOR_STORE_PROVIDER=postgresql` or `VECTOR_STORE_PROVIDER=sqlite` to use the alternate providers once their backing services are configured.

## CORS

Browser clients are controlled through `.env` CORS settings. Add deployed frontend origins to `CORS_ORIGINS` and keep MCP headers allowed/exposed:

```text
CORS_ORIGINS=http://localhost:9000,http://127.0.0.1:9000,https://your-frontend.example
CORS_ALLOW_HEADERS=Accept,Authorization,Content-Type,Last-Event-ID,Mcp-Session-Id,MCP-Protocol-Version,mcp-session-id,mcp-protocol-version
CORS_EXPOSE_HEADERS=Mcp-Session-Id,MCP-Session-Id,mcp-session-id,WWW-Authenticate
```

## Database Migrations

Alembic is the canonical schema-management path. The API runner applies migrations automatically:

```bash
python -m run
```

Manual migration commands:

```bash
.venv\Scripts\python -m alembic -c backend\alembic.ini upgrade head
.venv\Scripts\python -m alembic -c backend\alembic.ini downgrade -1
```

`AUTO_CREATE_TABLES=true` is only a development fallback and should stay disabled for normal use.

## OCR

Text files and digital PDFs work with the default install. For image files and scanned PDFs, install OCR dependencies and enable PaddleOCR:

```bash
.venv\Scripts\python -m pip install -e backend[ocr]
```

```text
OCR_PROVIDER=paddle
OCR_LANGUAGE=en
```

## Embeddings

The default development embedder is deterministic hashing. For production-quality local embeddings, install the embedding extra and enable Sentence Transformers:

```bash
.venv\Scripts\python -m pip install -e backend[embeddings]
```

```text
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
```

`BAAI/bge-small-en-v1.5` is the default production model target. Query embeddings use the BGE retrieval instruction; document chunk embeddings do not.

## Core Endpoints

- `GET /health`
- `GET /ready`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /api-keys`
- `GET /api-keys`
- `DELETE /api-keys/{api_key_id}`
- `POST /document-groups`
- `GET /document-groups`
- `GET /document-groups/{group_id}`
- `POST /document-groups/{group_id}/documents`
- `POST /document-groups/{group_id}/documents/upload`
- `GET /document-groups/{group_id}/documents`
- `GET /jobs/{job_id}`
- `POST /search`

Document creation and upload endpoints return `202 Accepted` with a `processing_job_id`.
Poll `GET /jobs/{job_id}` until the job reaches `completed` or `failed`.

## MCP Server

The API process mounts the streamable HTTP MCP endpoint at:

```text
/mcp
```

Users create an API key for a specific document group, then configure their AI platform with the hosted MCP URL and that key.
The key must be sent as an HTTP bearer token:

```text
Authorization: Bearer ormcp_...
```

When exposing MCP through a tunnel or reverse proxy, add the public host to:

```text
MCP_ALLOWED_HOSTS=127.0.0.1:8000,localhost:8000,home-8000.prasadsawant.site
MCP_ISSUER_URL=https://home-8000.prasadsawant.site
MCP_RESOURCE_SERVER_URL=https://home-8000.prasadsawant.site/mcp
```

The MCP server exposes:

- `list_document_groups`
- `list_documents`
- `search_documents`

Each tool uses the authenticated bearer token. The API key is never a tool argument, so it is not exposed to the LLM in tool schemas or calls. The key is scoped to one document group, so MCP tools return documents and search chunks from that group only.
