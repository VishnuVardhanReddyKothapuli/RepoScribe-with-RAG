import io
import json
import os
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

from evaluate import recall_at_k, run
from loader import allowed, repo_name, unpack
from main import Index, chunks, context_for, faithfulness, gemini, generate, validate_readme


class PipelineTests(unittest.TestCase):
    def test_url_allowlist(self):
        self.assertEqual(repo_name('https://github.com/psf/requests.git/'), 'psf/requests')
        for url in ('http://github.com/a/b', 'https://github.com.evil/a/b', 'https://github.com/a/b?x=1', 'https://localhost/a/b', 'file:///tmp/repo', 'https://github.com/../b'):
            with self.assertRaises(ValueError):
                repo_name(url)

    def test_file_filters(self):
        for path in ('.env', '.env.example', '../app.py', '/app.py', 'node_modules/app.js', 'secret.json', 'key.pem', 'image.png'):
            self.assertFalse(allowed(path), path)
        self.assertTrue(allowed('src/app.py'))

    def test_archive_limits_and_symlinks(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('repo/src/app.py', 'print("hello")')
            archive.writestr('repo/.env', 'secret=value')
            archive.writestr('repo/../../outside.py', 'bad')
            archive.writestr('repo/big.py', 'a' * 100001)
            archive.writestr('repo/binary.py', b'\x00')
            link = zipfile.ZipInfo('repo/link.py')
            link.external_attr = 0o120777 << 16
            archive.writestr(link, '/etc/passwd')
        files, scale = unpack(data.getvalue())
        self.assertEqual([f['path'] for f in files], ['src/app.py'])
        self.assertEqual(scale['skipped_files'], 5)

    def test_chunk_provenance_and_long_lines(self):
        text = 'x' * 10000 + '\nEND'
        result = chunks([{'path': 'src/a.py', 'content': text}])
        self.assertTrue(any('END' in c['text'] for c in result))
        self.assertTrue(all(len(c['text']) <= 3000 for c in result))
        self.assertEqual(result[0]['line'], 1)
        self.assertEqual(len({c['id'] for c in result}), len(result))

    def test_retrieval_and_no_evidence(self):
        index = Index([{'path': 'app.py', 'content': 'def greet(): print("hello")'}, {'path': 'package.json', 'content': 'installation dependencies typescript'}])
        for rerank in (False, True):
            self.assertEqual(index.retrieve('installation typescript', 1, rerank)[0]['path'], 'package.json')
            self.assertEqual(index.retrieve('unfindablequux', 5, rerank), [])
        self.assertEqual(Index([]).retrieve('anything'), [])
        self.assertLessEqual(sum(len(c['text']) for c in context_for(index)), 45000)
        with self.assertRaises(ValueError):
            index.retrieve('hello', 0)

    def test_recall_deduplicates_files(self):
        hits = [{'path': 'a'}, {'path': 'a'}, {'path': 'b'}]
        self.assertEqual(recall_at_k(hits, ['a', 'b'], 2), .5)
        self.assertEqual(recall_at_k(hits, ['a', 'b'], 3), 1)
        with self.assertRaises(ValueError):
            recall_at_k(hits, [], 5)

    def test_guardrails(self):
        evidence = [{'id': 'S1'}]
        validate_readme('# Project\nDocumented feature [S1]', evidence)
        validate_readme('Known [S1, S1]', evidence)
        for text in ('', 'No citation', 'Unknown [S9]', 'Unknown [S1, S99]', '-----BEGIN RSA PRIVATE KEY----- [S1]'):
            with self.assertRaises(ValueError):
                validate_readme(text, evidence)

    def test_credentials_redacted_before_retrieval(self):
        credential = 'AIza' + 'a' * 35
        result = chunks([{'path': 'app.py', 'content': 'token = ' + credential}])
        self.assertNotIn(credential, result[0]['text'])
        self.assertIn('[REDACTED]', result[0]['text'])

    def test_generation_uses_shared_evidence(self):
        repo = {'name': 'test/repo', 'revision': 'a' * 40, 'files': [{'path': 'README.md', 'content': 'Project installation usage tests license'}], 'scale': {'loaded_files': 1}}
        with patch('main.gemini', return_value='# Test\nProject usage [S1]') as provider:
            result = generate(repo)
        self.assertEqual(result['evidence'][0]['path'], 'README.md')
        self.assertIn('untrusted', provider.call_args.args[0])
        self.assertGreaterEqual(result['metrics']['total_ms'], result['metrics']['retrieval_ms'])

    def test_faithfulness_denominator(self):
        with patch('main.gemini', return_value=json.dumps({'claims': [{'verdict': 'supported', 'evidence_id': 'S1', 'quote': 'hello'}, {'verdict': 'unsupported'}, {'verdict': 'insufficient'}]})):
            self.assertAlmostEqual(faithfulness('answer', [{'id': 'S1', 'text': 'hello world'}])['score'], 1 / 3)
        with patch('main.gemini', return_value=json.dumps({'claims': [{'verdict': 'supported', 'evidence_id': 'S1', 'quote': 'invented'}]})):
            self.assertEqual(faithfulness('answer', [{'id': 'S1', 'text': 'hello world'}])['score'], 0)
        with patch('main.gemini', return_value='{"claims": []}'):
            with self.assertRaises(ValueError):
                faithfulness('answer', [])
        with patch('main.gemini', return_value='[]'):
            with self.assertRaises(ValueError):
                faithfulness('answer', [])

    def test_provider_retries_and_rejects_truncation(self):
        payload = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'ok'}]}}]}
        unavailable = urllib.error.HTTPError('https://provider.invalid', 503, 'busy', {}, None)
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test'}), patch('main.time.sleep'), patch('main.urllib.request.urlopen', side_effect=[unavailable, io.BytesIO(json.dumps(payload).encode())]) as request:
            self.assertEqual(gemini('system', {}), 'ok')
            self.assertEqual(request.call_count, 2)
        payload['candidates'][0]['finishReason'] = 'MAX_TOKENS'
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test'}), patch('main.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(RuntimeError):
                gemini('system', {})

    def test_dataset_runs_without_api_calls(self):
        with patch('main.gemini', side_effect=AssertionError('Offline run called the provider')):
            report = list(run(Path('evaluations/cases.json'), repeats=1))[-1]
        self.assertEqual(len(report['repositories']), 3)
        for repo in report['repositories']:
            self.assertEqual(len(repo['revision']), 40)
            for variant in repo['variants'].values():
                self.assertIsNone(variant['faithfulness'])
                self.assertIsNone(variant['generation'])
                self.assertTrue(all(0 <= value <= 1 for value in variant['recall'].values()))


class ApiTests(unittest.TestCase):
    def test_key_and_url_validation(self):
        from api import GenerateRequest, create_readme, health
        from fastapi import HTTPException
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(health()['ready'])
            with self.assertRaises(HTTPException) as error:
                create_readme(GenerateRequest(repo_url='https://github.com/psf/requests'))
            self.assertEqual(error.exception.status_code, 503)
        with self.assertRaises(HTTPException) as error:
            create_readme(GenerateRequest(repo_url='https://127.0.0.1/private'))
        self.assertEqual(error.exception.status_code, 400)

    def test_api_success_and_lock_release(self):
        from api import GenerateRequest, busy, create_readme
        from fastapi import HTTPException
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}), patch('api.load_repository', return_value={}), patch('api.generate', return_value={'readme': 'test', 'metrics': {}}):
            self.assertEqual(create_readme(GenerateRequest(repo_url='https://github.com/a/b'))['readme'], 'test')
            self.assertFalse(busy.locked())
            busy.acquire()
            try:
                with self.assertRaises(HTTPException) as error:
                    create_readme(GenerateRequest(repo_url='https://github.com/a/b'))
                self.assertEqual(error.exception.status_code, 429)
            finally:
                busy.release()


class DeploymentTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(Path('frontend/dist/index.html').is_file(), 'Build the frontend before testing production serving.')
    async def test_frontend_and_api_share_one_server(self):
        from api import app
        import re

        async def get(path):
            messages = []

            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}

            async def send(message):
                messages.append(message)

            await app({'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.4'},
                       'method': 'GET', 'path': path, 'raw_path': path.encode(), 'root_path': '',
                       'query_string': b'', 'headers': [], 'scheme': 'http',
                       'server': ('test', 80), 'client': ('test', 1234), 'http_version': '1.1'}, receive, send)
            return messages[0]['status'], b''.join(m.get('body', b'') for m in messages)

        status, page = await get('/')
        self.assertEqual(status, 200)
        self.assertIn(b'id="root"', page)
        asset = re.search(rb'src="(/assets/[^"]+)"', page)[1].decode()
        self.assertEqual((await get(asset))[0], 200)
        status, body = await get('/api/health')
        self.assertEqual(status, 200)
        self.assertIn('ready', json.loads(body))
        for path in ('/.env', '/api/unknown', '/assets/missing.js'):
            self.assertEqual((await get(path))[0], 404)


if __name__ == '__main__':
    unittest.main()
