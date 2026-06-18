from typing import Any

__all__ = ["RagChain", "rag_chain"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from app.generation.rag_chain import RagChain, rag_chain

        return {"RagChain": RagChain, "rag_chain": rag_chain}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
