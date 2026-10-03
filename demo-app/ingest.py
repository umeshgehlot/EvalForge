"""Run once to embed and store documents in pgvector."""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.litellm import LiteLLM

load_dotenv()

EMBED_DIM = 1536


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment", file=sys.stderr)
        sys.exit(1)

    p = urlparse(db_url)
    db = {
        "user": p.username,
        "password": p.password,
        "host": p.hostname,
        "port": p.port or 5432,
        "database": p.path.lstrip("/"),
    }

    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.llm = LiteLLM(model=os.getenv("LLM_MODEL", "gpt-4o-mini"))
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50

    vector_store = PGVectorStore.from_params(
        database=db["database"],
        host=db["host"],
        password=db["password"],
        port=db["port"],
        user=db["user"],
        table_name="rag_documents",
        embed_dim=EMBED_DIM,
    )

    docs_path = Path(__file__).parent / "documents"
    if not docs_path.exists():
        print(f"ERROR: documents/ directory not found at {docs_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading documents from {docs_path} ...")
    docs = SimpleDirectoryReader(str(docs_path)).load_data()
    file_count = len({d.metadata.get("file_name") for d in docs})
    print(f"  Loaded {len(docs)} chunks from {file_count} files")

    print("Embedding and indexing (this may take a minute) ...")
    VectorStoreIndex.from_documents(
        docs,
        storage_context=StorageContext.from_defaults(vector_store=vector_store),
        show_progress=True,
    )

    print("Ingestion complete.")


if __name__ == "__main__":
    main()
