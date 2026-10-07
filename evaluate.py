"""Reproducible retrieval baseline, reranking ablation, and optional live generation/judging."""
import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from app.rag.splitter import chunks
from app.rag.retriever import BM25Retriever
from app.services.readme_generator import faithfulness, generate

ROOT = Path(__file__).resolve().parent


def recall_at_k(hits, relevant, k):
    if not relevant:
        raise ValueError('Recall requires at least one relevant file.')
    return len({h['path'] for h in hits[:k]} & set(relevant)) / len(set(relevant))


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def run(dataset, live=False, repeats=5):
    spec = json.loads(dataset.read_text(encoding='utf-8'))
    report = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(), 'platform': platform.platform(), 'repeats': repeats,
              'dataset_sha256': hashlib.sha256(dataset.read_bytes()).hexdigest(),
              'pipeline_sha256': hashlib.sha256((ROOT / 'main.py').read_bytes()).hexdigest(),
              'retrieval': 'BM25 baseline vs optional lexical coverage/path reranker; not a comparison to the old embedding script',
              'faithfulness_method': 'Live LLM judge, not a lexical proxy; null when not run',
              'model': os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite') if live else None, 'repositories': []}
    controls_path = dataset.parent / 'guardrails.json'
    if live and controls_path.exists():
        controls = json.loads(controls_path.read_text(encoding='utf-8'))
        report['guardrail_controls'] = []
        for control in controls['faithfulness_controls']:
            try:
                judged = faithfulness(control['readme'], control['evidence'])
                report['guardrail_controls'].append({'id': control['id'], 'passed': judged['score'] == control['expected_score'], 'result': judged})
            except (ValueError, RuntimeError) as error:
                report['guardrail_controls'].append({'id': control['id'], 'passed': False, 'error': str(error)})
        injection = controls['generation_injection']
        try:
            generated = generate(injection)
            report['guardrail_controls'].append({'id': 'generation-injection', 'passed': injection['forbidden_output'] not in generated['readme'], 'generation': generated,
                                                 'scope': 'Checks one planted marker only; not a proof of prompt-injection immunity.'})
        except (ValueError, RuntimeError) as error:
            report['guardrail_controls'].append({'id': 'generation-injection', 'passed': False, 'error': str(error)})
    for item in spec['repositories']:
        snapshot = dataset.parent / item['snapshot']
        repo = json.loads(snapshot.read_text(encoding='utf-8'))
        paths = {f['path'] for f in repo['files']}
        started = time.perf_counter()
        index = BM25Retriever(chunks(repo['files']))
        index_ms = (time.perf_counter() - started) * 1000
        record = {'name': repo['name'], 'url': repo['url'], 'revision': repo['revision'],
                  'snapshot_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                  'scale': {**repo['scale'], 'chunks': len(index.chunks)}, 'index_ms': index_ms, 'variants': {}}
        for rerank in (False, True):
            rows, timings = [], []
            for case in item['cases']:
                if not set(case['relevant_files']) <= paths:
                    raise ValueError(f"Missing relevance labels in {case['id']}")
                index.retrieve(case['query'], 5, rerank)  # warm-up, excluded from latency
                for _ in range(repeats):
                    started = time.perf_counter()
                    index.retrieve(case['query'], 5, rerank)
                    timings.append((time.perf_counter() - started) * 1000)
                hits_by_k = {str(k): index.retrieve(case['query'], k, rerank) for k in (1, 3, 5, 10)}
                rows.append({**case, 'retrieved': {k: [{'id': h['id'], 'path': h['path'], 'line': h['line']} for h in hits] for k, hits in hits_by_k.items()},
                             'recall': {k: recall_at_k(hits, case['relevant_files'], int(k)) for k, hits in hits_by_k.items()}})
            variant = {'cases': rows, 'recall': {str(k): statistics.mean(r['recall'][str(k)] for r in rows) for k in (1, 3, 5, 10)},
                       'latency_ms': {'k': 5, 'p50': statistics.median(timings), 'p95': percentile(timings, .95), 'samples': len(timings)},
                       'generation': None, 'faithfulness': None, 'status': 'not_run_offline_mode' if not live else 'pending'}
            if live:
                try:
                    variant['generation'] = generate(repo, rerank)
                    variant['status'] = 'generated_judge_pending'
                    started = time.perf_counter()
                    variant['faithfulness'] = faithfulness(variant['generation']['readme'], variant['generation']['evidence'])
                    variant['judge_ms'] = (time.perf_counter() - started) * 1000
                    variant['status'] = 'complete'
                except (ValueError, RuntimeError) as error:
                    variant['status'] = 'failed'
                    variant['error'] = str(error)
            record['variants']['reranked' if rerank else 'baseline'] = variant
        report['repositories'].append(record)
        yield report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'evaluations/cases.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluations/baseline.json')
    parser.add_argument('--live', action='store_true', help='Generate 6 repository READMEs, judge each and run 4 controls; incurs provider usage.')
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    if args.live:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        pass
            pass
    for report in run(args.dataset, args.live, args.repeats):
        save(args.output, report)
        record = report['repositories'][-1]
        print(record['name'], {name: v['recall'] for name, v in record['variants'].items()}, flush=True)
    if args.live and (any(v['status'] != 'complete' for r in report['repositories'] for v in r['variants'].values()) or any(not c['passed'] for c in report.get('guardrail_controls', []))):
        raise SystemExit('Some live evaluations failed; partial results and errors are saved in the report.')
