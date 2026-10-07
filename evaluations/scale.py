"""Synthetic size/latency stress check, separate from real-repository relevance scores."""
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.retriever import BM25Retriever
from app.rag.splitter import chunks
from evaluate import percentile, save


if __name__ == '__main__':
    root = Path(__file__).parent
    repository = json.loads((root / 'pallets_itsdangerous.json').read_text(encoding='utf-8'))
    report = {'method': 'Synthetic duplicates of the pinned ItsDangerous snapshot. Timing/scale only; not retrieval-quality evidence. Index time is measured under tracemalloc.', 'source_revision': repository['revision'], 'rows': []}
    for copies in (1, 5, 10, 20):
        files = [dict(f, path=f"copy-{n}/{f['path']}") for n in range(copies) for f in repository['files']]
        tracemalloc.start()
        started = time.perf_counter()
        index = BM25Retriever(chunks(files))
        index_ms = (time.perf_counter() - started) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        row = {'files': len(files), 'bytes': sum(len(f['content'].encode()) for f in files), 'chunks': len(index.chunks), 'index_ms': index_ms, 'index_peak_bytes': peak, 'latency_ms': {}}
        for rerank in (False, True):
            samples = []
            for _ in range(11):
                started = time.perf_counter()
                index.retrieve('TimestampSigner max_age expired signature', 5, rerank)
                samples.append((time.perf_counter() - started) * 1000)
            samples = samples[1:]
            row['latency_ms']['reranked' if rerank else 'baseline'] = {'p50': statistics.median(samples), 'p95': percentile(samples, .95), 'samples': len(samples)}
        report['rows'].append(row)
        print(row, flush=True)
    save(root / 'scale.json', report)
