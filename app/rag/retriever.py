import math
import re
from collections import Counter
from typing import List, Dict, Any

STOP = set('the a an is are in of to for and or how what does this with on from it'.split())

def tokens(text: str) -> List[str]:
    return [word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP]

class BM25Retriever:
    def __init__(self, document_chunks: List[Dict[str, Any]]):
        self.chunks = document_chunks
        self.counts = [Counter(tokens(c['path'] + ' ' + c['text'])) for c in self.chunks]
        self.df = Counter(term for counts in self.counts for term in counts)
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(1, len(self.lengths)) or 1

    def retrieve(self, query: str, k: int = 5, rerank: bool = False) -> List[Dict[str, Any]]:
        if not 1 <= k <= 20:
            raise ValueError('K must be between 1 and 20.')
        terms = set(tokens(query))
        scored = []
        for chunk, counts, length in zip(self.chunks, self.counts, self.lengths):
            score = sum(
                math.log(1 + (len(self.chunks) - self.df[t] + 0.5) / (self.df[t] + 0.5))
                * counts[t] * 2.5 / (counts[t] + 1.5 * (0.25 + 0.75 * length / self.average))
                for t in terms if counts[t]
            )
            if score > 0:
                scored.append((score, chunk))
        
        scored.sort(key=lambda pair: (-pair[0], pair[1]['id']))
        candidates = scored[:max(k * 4, 20)]
        
        if rerank:
            candidates.sort(key=lambda pair: (
                -(len(terms & set(tokens(pair[1]['text']))) / max(1, len(terms))
                  + 0.25 * len(terms & set(tokens(pair[1]['path'])))),
                -pair[0]
            ))
            
        return [dict(chunk, score=round(score, 4)) for score, chunk in candidates[:k]]
