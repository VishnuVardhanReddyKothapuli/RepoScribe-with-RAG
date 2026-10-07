from typing import List, Dict, Any
from app.rag.retriever import BM25Retriever

QUERIES = [
    'project overview features public API',
    'installation dependencies requirements package setup',
    'usage examples command line',
    'configuration environment variables',
    'tests contributing license'
]

def retrieve_relevant_context(retriever: BM25Retriever, rerank: bool = False) -> List[Dict[str, Any]]:
    selected = {}
    for query in QUERIES:
        for chunk in retriever.retrieve(query, 4, rerank):
            selected[chunk['id']] = chunk
            
    evidence = []
    size = 0
    for chunk in selected.values():
        if size + len(chunk['text']) <= 45000:
            evidence.append(chunk)
            size += len(chunk['text'])
            
    return evidence
