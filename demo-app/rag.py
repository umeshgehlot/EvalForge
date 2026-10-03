import time
import tiktoken
from typing import Dict, Any, List
from urllib.parse import urlparse

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.litellm import LiteLLM

from tracer import tracer, start_trace, flush_spans

EMBED_DIM = 1536  # text-embedding-3-small default


def _parse_db_url(db_url: str) -> dict:
    p = urlparse(db_url)
    return {
        "user": p.username,
        "password": p.password,
        "host": p.hostname,
        "port": p.port or 5432,
        "database": p.path.lstrip("/"),
    }


class RAGPipeline:
    def __init__(self, db_url: str, model: str = "gpt-4o-mini"):
        self.model = model

        self.token_counter = TokenCountingHandler(
            tokenizer=tiktoken.encoding_for_model("gpt-4o-mini").encode,
            verbose=False,
        )

        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        Settings.llm = LiteLLM(model=model)
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50
        Settings.callback_manager = CallbackManager([self.token_counter])

        db = _parse_db_url(db_url)
        self.vector_store = PGVectorStore.from_params(
            database=db["database"],
            host=db["host"],
            password=db["password"],
            port=db["port"],
            user=db["user"],
            table_name="rag_documents",
            embed_dim=EMBED_DIM,
        )

        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=StorageContext.from_defaults(
                vector_store=self.vector_store
            ),
        )

    def ask(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        self.token_counter.reset_counts()
        start_trace()

        with tracer.start_as_current_span("rag.total") as total_span:
            total_span.set_attribute("question", question[:500])
            total_span.set_attribute("top_k", top_k)

            # ── Retrieval ────────────────────────────────────────────────────
            with tracer.start_as_current_span("rag.retrieval") as ret_span:
                retriever = self.index.as_retriever(similarity_top_k=top_k)
                nodes = retriever.retrieve(question)
                ret_span.set_attribute("nodes_retrieved", len(nodes))
                ret_span.set_attribute("top_k", top_k)

            # ── Generation ───────────────────────────────────────────────────
            with tracer.start_as_current_span("rag.generate") as gen_span:
                synthesizer = get_response_synthesizer(llm=Settings.llm)
                response = synthesizer.synthesize(question, nodes=nodes)
                gen_span.set_attribute("model", self.model)
                gen_span.set_attribute(
                    "token_in", self.token_counter.prompt_llm_token_count
                )
                gen_span.set_attribute(
                    "token_out", self.token_counter.completion_llm_token_count
                )

        chunks: List[Dict[str, Any]] = []
        for node in nodes:
            chunks.append(
                {
                    "text": node.node.text,
                    "source": node.node.metadata.get("file_name", "unknown"),
                    "score": (
                        round(float(node.score), 4) if node.score is not None else None
                    ),
                }
            )

        # Compute latency from the root span timestamps (nanoseconds → ms)
        finished = flush_spans()
        root = next((s for s in finished if s["span_name"] == "rag.total"), None)
        latency_ms = (
            int(root["end_ms"] - root["start_ms"]) if root else 0
        )

        return {
            "answer": str(response),
            "retrieved_chunks": chunks,
            "latency_ms": latency_ms,
            "tokens": {
                "input": self.token_counter.prompt_llm_token_count,
                "output": self.token_counter.completion_llm_token_count,
            },
            "spans": finished,
        }
