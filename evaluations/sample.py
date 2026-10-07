"""Recreate the seeded sample; existing snapshots stay pinned unless --refresh is used."""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.loader import load_repository

POOL = ['pallets/click', 'psf/requests', 'sindresorhus/is', 'pallets/itsdangerous']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    for name in random.Random(42).sample(POOL, 3):
        path = Path(__file__).parent / (name.replace('/', '_') + '.json')
        if path.exists() and not args.refresh:
            continue
        repo = load_repository('https://github.com/' + name)
        path.write_text(json.dumps(repo, indent=2), encoding='utf-8')
        print(name, repo['revision'], repo['scale'], flush=True)
