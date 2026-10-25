import time
from collections.abc import Iterator

from app.core.config import settings
from app.generation.confidence import has_strong_context
from app.guardrails import (
    OUT_OF_SCOPE_ANSWER,
    check_scope,
    contains_prompt_injection,
    filter_safe_history,
)
from app.generation.llm import answer_with_llm
from app.generation.citations import public_citations
from app.generation.multi_query import VietnameseMultiQueryGenerator
from app.generation.query_rewriter import VietnameseQueryRewriter
from app.retrieval import Retriever, retriever
from app.retrieval.multi_query import fuse_multi_query_results
from app.retrieval.reranker import Reranker

NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."

DEBUG_CHUNK_FIELDS = (
    "chunk_id",
    "document_id",
    "source",
    "source_name",
    "heading",
    "section_path",
    "chunk_index",
    "parent_id",
    "parent_index",
    "child_index",
    "evidence_text",
    "matched_child_ids",
    "matched_child_count",
    "text",
    "score",
    "vector_score",
    "bm25_score",
    "rrf_score",
    "rerank_score",
    "query_hits",
)


def _debug_chunk(context: dict, rank: int) -> dict:
    """Build a JSON-safe snapshot of a retrieved chunk for persisted debugging."""
    snapshot = {"rank": rank}
    for field in DEBUG_CHUNK_FIELDS:
        value = context.get(field)
        if value is not None:
            snapshot[field] = float(value) if field.endswith("score") else value
    return snapshot


from app.llm import BaseLLMProvider


class RagChain:
    def __init__(
        self,
        retriever_: Retriever | None = None,
        query_rewriter: VietnameseQueryRewriter | None = None,
        multi_query_generator: VietnameseMultiQueryGenerator | None = None,
        reranker: Reranker | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        self.retriever = retriever_ or retriever
        self.query_rewriter = query_rewriter or VietnameseQueryRewriter()
        self.multi_query_generator = multi_query_generator or VietnameseMultiQueryGenerator()
        self.reranker = reranker or Reranker()
        self.llm_provider = llm_provider

    def answer(
        self,
        question: str,
        top_k: int = 4,
        history: list[dict[str, str]] | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ) -> dict:
        safe_history = filter_safe_history(history)
        result = self.retrieve_context(question, top_k=top_k, history=safe_history)
        if not result["guardrail_allowed"]:
            return {
                "answer": OUT_OF_SCOPE_ANSWER,
                "sources": [],
                "contexts": [],
                "retrieval_debug": result["retrieval_debug"],
            }
        if not result["strong_context"]:
            return {
                "answer": NO_CONTEXT_ANSWER,
                "sources": [],
                "contexts": [],
                "retrieval_debug": result["retrieval_debug"],
            }

        provider = llm_provider or self.llm_provider
        answer = answer_with_llm(question, result["contexts"], history=safe_history, provider=provider)
        return {
            "answer": answer,
            "sources": public_citations(result["contexts"]),
            "contexts": result["contexts"],
            "retrieval_debug": result["retrieval_debug"],
        }

    def retrieve_context(
        self,
        question: str,
        top_k: int = 4,
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        """Run retrieval independently so callers can stream generation."""
        for event in self.iter_retrieve_context(question, top_k=top_k, history=history):
            if "result" in event:
                return event["result"]
        # iter_retrieve_context luôn kết thúc bằng event result nên không tới đây.
        raise RuntimeError("iter_retrieve_context ended without a result event.")

    def iter_retrieve_context(
        self,
        question: str,
        top_k: int = 4,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[dict]:
        """Yield progress events for each retrieval stage, then the result.

        Mỗi event bước có dạng ``{"step": str, "detail": dict, "elapsed_ms": int}``
        (elapsed_ms là thời gian của chính bước đó). Event cuối cùng mang key
        ``"result"`` với đúng shape của :meth:`retrieve_context` để caller lấy
        kết quả mà không phải chạy lại retrieval.
        """
        step_started = time.perf_counter()

        def step_event(step: str, detail: dict | None = None) -> dict:
            nonlocal step_started
            elapsed_ms = round((time.perf_counter() - step_started) * 1000)
            step_started = time.perf_counter()
            return {"step": step, "detail": detail or {}, "elapsed_ms": elapsed_ms}

        scope_allowed = True
        scope_reason = "disabled"
        if settings.guardrail_scope_enabled:
            scope = check_scope(question, history)
            scope_allowed = scope.allowed
            scope_reason = scope.reason
        yield step_event("guardrail", {"allowed": scope_allowed, "reason": scope_reason})
        if not scope_allowed:
            retrieval_debug = {
                "original_query": question,
                "rewritten_query": "",
                "retrieval_queries": [],
                "requested_top_k": top_k,
                "candidate_count": 0,
                "retrieved_chunks": [],
                "selected_chunks": [],
                "strong_context": False,
                "guardrail": {"allowed": False, "reason": scope_reason},
            }
            yield {
                "result": {
                    "contexts": [],
                    "retrieval_debug": retrieval_debug,
                    "strong_context": False,
                    "guardrail_allowed": False,
                }
            }
            return

        rewritten_query = self.query_rewriter.rewrite(question, history=history)
        yield step_event("query_rewrite", {"rewritten_query": rewritten_query})
        queries = self.multi_query_generator.generate(rewritten_query)
        yield step_event("multi_query", {"queries": queries})
        candidate_count = (
            max(top_k, top_k * settings.reranker_candidate_multiplier)
            if settings.reranker_enabled
            else top_k
        )
        result_sets = [
            self.retriever.retrieve(query, top_k=candidate_count)
            for query in queries
        ]
        contexts = fuse_multi_query_results(result_sets, top_k=candidate_count)
        unsafe_context_count = sum(
            contains_prompt_injection(str(context.get("text", "")))
            for context in contexts
        )
        contexts = [
            context
            for context in contexts
            if not contains_prompt_injection(str(context.get("text", "")))
        ]
        retrieved_chunks = [
            _debug_chunk(context, rank)
            for rank, context in enumerate(contexts, start=1)
        ]
        # Tên tài liệu distinct (giữ thứ tự xuất hiện) để UI gợi ý kho đang hit.
        hit_sources: list[str] = []
        for context in contexts:
            name = context.get("source_name") or context.get("source")
            if name and name not in hit_sources:
                hit_sources.append(str(name))
        yield step_event(
            "retrieve",
            {
                "candidate_count": len(contexts),
                "queries": queries,
                "sources": hit_sources[:3],
                "unsafe_contexts_removed": unsafe_context_count,
            },
        )
        if settings.reranker_enabled:
            contexts = self.reranker.rerank(rewritten_query, contexts, top_k=top_k)
        else:
            contexts = contexts[:top_k]
        selected_chunks = [
            _debug_chunk(context, rank)
            for rank, context in enumerate(contexts, start=1)
        ]
        yield step_event("rerank", {"selected_count": len(contexts), "enabled": settings.reranker_enabled})
        strong_context = has_strong_context(
            contexts,
            min_vector_score=settings.retrieval_min_vector_score,
            min_bm25_score=settings.retrieval_min_bm25_score,
        )
        retrieval_debug = {
            "original_query": question,
            "rewritten_query": rewritten_query,
            "retrieval_queries": queries,
            "requested_top_k": top_k,
            "candidate_count": candidate_count,
            "retrieved_chunks": retrieved_chunks,
            "selected_chunks": selected_chunks,
            "strong_context": strong_context,
            "guardrail": {"allowed": True, "reason": scope_reason},
            "unsafe_contexts_removed": unsafe_context_count,
        }
        yield {
            "result": {
                "contexts": contexts,
                "retrieval_debug": retrieval_debug,
                "strong_context": strong_context,
                "guardrail_allowed": True,
            }
        }


rag_chain = RagChain()
