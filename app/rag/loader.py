"""Bounded public GitHub snapshots. Repository code is never executed."""
import io
import json
import re
import urllib.request
import zipfile
from pathlib import PurePosixPath
from app.config import settings

MAX_ARCHIVE = settings.max_archive_bytes
MAX_BYTES = settings.max_total_bytes
MAX_FILE = settings.max_file_bytes
MAX_FILES = settings.max_files
SKIP = {'.git', 'node_modules', '.venv', 'venv', 'dist', 'build', '__pycache__', 'vendor'}
EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.rb', '.md', '.rst', '.txt', '.toml', '.json', '.yaml', '.yml', '.sh', '.cfg', '.ini'}
SECRET = re.compile(r'AIza[\w-]{30,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----')


def redact(text):
    return SECRET.sub(lambda match: '[REDACTED]' + '\n' * match[0].count('\n'), text)


def repo_name(url):
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?', url)
    if not match or any(part in {'.', '..'} for part in match[1].split('/')):
        raise ValueError('Use a public https://github.com/owner/repository URL.')
    return match[1]


def fetch(url, limit):
    headers = {'User-Agent': 'RepoScribe', 'Accept': 'application/vnd.github+json'}
    if settings.github_token:
        headers['Authorization'] = f'Bearer {settings.github_token}'
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Repository download exceeds the configured size limit.')
    return data


def allowed(path):
    p = PurePosixPath(path)
    return (not p.is_absolute() and '..' not in p.parts and not SKIP.intersection(p.parts)
            and not any(part.startswith('.env') for part in p.parts)
            and not any(word in p.name.lower() for word in ('secret', 'credential', 'private_key', 'package-lock', 'yarn.lock'))
            and (p.suffix.lower() in EXTENSIONS or p.name in {'Dockerfile', 'Makefile', 'LICENSE'}))


def unpack(data):
    files, skipped, total, seen = [], 0, 0, 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = sorted(archive.infolist(), key=lambda item: (item.filename.count('/'), item.filename))
        for entry in entries:
            if entry.is_dir():
                continue
            seen += 1
            path = entry.filename.partition('/')[2]
            symlink = (entry.external_attr >> 16) & 0o170000 == 0o120000
            if not path or symlink or not allowed(path) or entry.file_size > MAX_FILE or len(files) >= MAX_FILES or total + entry.file_size > MAX_BYTES:
                skipped += 1
                continue
            raw = archive.read(entry)
            try:
                content = raw.decode('utf-8')
            except UnicodeDecodeError:
                skipped += 1
                continue
            if '\x00' in content:
                skipped += 1
                continue
            files.append({'path': path, 'content': redact(content)})
            total += len(raw)
    if not files:
        raise ValueError('No supported text files found.')
    return files, {'repository_files': seen, 'loaded_files': len(files), 'skipped_files': skipped, 'loaded_bytes': total}


def load_repository(url, revision=None):
    name = repo_name(url)
    if revision is None:
        revision = json.loads(fetch(f'https://api.github.com/repos/{name}/commits/HEAD', 1_000_000))['sha']
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Revision must be a full commit SHA.')
    files, scale = unpack(fetch(f'https://codeload.github.com/{name}/zip/{revision}', MAX_ARCHIVE))
    return {'url': f'https://github.com/{name}', 'name': name, 'revision': revision, 'files': files, 'scale': scale}
