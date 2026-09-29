# Evaluation results

Measured: 2026-09-29T10:27:51.089994+00:00. Model: `gemini-3.1-flash-lite`.

Three commit-pinned public repositories; 12 labeled retrieval queries, six generated READMEs, four synthetic live controls. Each generated README and its full evidence and judge output are saved in [live.json](live.json).

| Repository | Loaded files | Chunks | Recall@5 baseline / reranked | Recall@10 baseline / reranked | Conservative faithfulness baseline / reranked |
|---|---:|---:|---:|---:|---:|
| pallets/click | 155 | 514 | 37.5% / 50.0% | 87.5% / 62.5% | 46.7% / 50.0% |
| pallets/itsdangerous | 42 | 67 | 87.5% / 75.0% | 100.0% / 75.0% | 100.0% / 20.0% |
| psf/requests | 92 | 280 | 50.0% / 50.0% | 75.0% / 75.0% | 35.7% / 23.1% |

Macro averages: Recall@5 **58.3% / 58.3%**, Recall@10 **87.5% / 70.8%**, conservative faithfulness **60.8% / 31.0%** (baseline / reranked). Reranking remains off by default.

## Latency

| Repository | Index ms | Retrieval p50/p95 ms baseline | Retrieval p50/p95 ms reranked | Generation seconds baseline / reranked |
|---|---:|---:|---:|---:|
| pallets/click | 72.72 | 1.61 / 1.83 | 3.91 / 4.85 | 10.20 / 7.96 |
| pallets/itsdangerous | 8.62 | 0.15 / 0.16 | 1.68 / 1.99 | 6.37 / 7.60 |
| psf/requests | 36.64 | 0.70 / 0.81 | 3.15 / 3.56 | 5.79 / 5.48 |

Retrieval timings use five repetitions per query at K=5 after warm-up. Generation has one sample per repository/variant. Indexing and generation are excluded from retrieval timings; remote repository downloading is excluded from snapshot runs. Timings describe this machine and run, not service guarantees.

## Scale and checks

- Natural snapshots: 42-155 loaded files, 98 KB-1.03 MB text, 67-514 chunks.
- Synthetic stress run: 42, 210, 420, and 840 files; up to 1.96 MB text and 1,340 chunks. The largest run used about 10.5 MB traced indexing allocations. See [scale.json](scale.json).
- All four live controls passed: supported claim, hallucinated feature, judge injection, and one generation-injection marker.
- 14 Python regression tests pass. Strict TypeScript and production build pass. Browser checks cover error recovery, generation, preview/Markdown, evidence expansion, download, keyboard access, and responsive widths.

## Interpretation

The score is conservative evidence-backed faithfulness: a supported claim also requires the judge to quote an exact substring of the cited passage. Unverifiable quotes count as insufficient. This catches invented evidence but also penalizes judge quotation errors; these scores are not human-labeled factual accuracy. Raw judge verdicts and reasons are retained when downgraded.

The sample is small, Python-only, includes existing upstream READMEs, and uses incomplete manually selected relevant-file labels. It is a smoke benchmark, not a held-out or representative evaluation. Synthetic scale duplicates measure cost, not quality. The same generator/judge model may share biases. Passing four controls is not a guarantee against arbitrary prompt injection.

BM25 is a new shared baseline replacing the previously disconnected vector script and Streamlit prompt path. No quality comparison to the old embedding implementation is claimed.

Reproduce with `python evaluate.py`, `python evaluations/scale.py`, and `python evaluate.py --live --output evaluations/live.json` from the project root. Live mode requires the configured server key and incurs provider usage.
