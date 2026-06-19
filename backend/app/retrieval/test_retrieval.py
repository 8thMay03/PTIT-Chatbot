from app.retrieval.retriever import Retriever

if __name__ == "__main__":
    retriever = Retriever()
    chunks = retriever.retrieve("Mức học bổng của PTIT là bao nhiêu?")
    for chunk in chunks:
        print(chunk)
        print("-" * 100)