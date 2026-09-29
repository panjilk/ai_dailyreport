import hashlib
import json
from unittest.mock import patch

import pytest
import requests

from dailyreport import international as tr


class Response:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f'{self.status_code} Client Error')
            error.response = self
            raise error

    def json(self):
        return {'choices': [{'message': {'content': self.content}}]}


@pytest.fixture(autouse=True)
def local_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(tr, 'CACHE_PATH', tmp_path / 'translation_cache.json')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setattr(tr.time, 'sleep', lambda _: None)


def test_cache_hit_skips_request():
    original = 'GPT-6  has   arrived.'
    digest = hashlib.sha256(b'GPT-6 has arrived.').hexdigest()
    tr.CACHE_PATH.write_text(json.dumps({digest: {'zh': 'GPT-6 已发布。',
        'model': 'deepseek-chat', 'ts': '2026-09-29T00:00:00+00:00'}}), encoding='utf-8')
    assert tr.translate_to_chinese(original, lambda *_a, **_k: pytest.fail('发出了请求')) == 'GPT-6 已发布。'


def test_success_writes_cache_and_reloads():
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs)
        return Response('模型已发布。')
    assert tr.translate_to_chinese('The model was released.', post) == '模型已发布。'
    assert tr.translate_to_chinese('The  model was released.', post) == '模型已发布。'
    assert len(calls) == 1
    entry = next(iter(json.loads(tr.CACHE_PATH.read_text(encoding='utf-8')).values()))
    assert entry['model'] == 'deepseek-chat' and entry['zh'] == '模型已发布。' and entry['ts']
    assert calls[0]['json']['temperature'] == 0 and calls[0]['timeout'] == 30


def test_broken_cache_does_not_crash():
    tr.CACHE_PATH.write_text('{broken', encoding='utf-8')
    with pytest.warns(RuntimeWarning, match='缓存'):
        assert tr.translate_to_chinese('The model was released.',
            lambda *_a, **_k: Response('模型已发布。')) == '模型已发布。'


def test_missing_fields_treats_cache_as_empty():
    tr.CACHE_PATH.write_text('{"key": {"zh": "中文"}}', encoding='utf-8')
    with pytest.warns(RuntimeWarning, match='缓存'):
        assert tr.translate_to_chinese('The model was released.',
            lambda *_a, **_k: Response('模型已发布。')) == '模型已发布。'


def test_429_retries_then_succeeds():
    calls = []
    def post(*_a, **_k):
        calls.append(1)
        return Response('模型已发布。', 429 if len(calls) == 1 else 200)
    assert tr.translate_to_chinese('The model was released.', post) == '模型已发布。'
    assert len(calls) == 2


def test_persistent_429_raises():
    calls = []
    with pytest.raises(ValueError, match='请求失败'):
        tr.translate_to_chinese('The model was released.',
            lambda *_a, **_k: (calls.append(1), Response('', 429))[1])
    assert len(calls) == 4


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY')
    with pytest.raises(ValueError, match='缺少 DEEPSEEK_API_KEY，无法翻译英文条目'):
        tr.translate_to_chinese('The model was released.', lambda *_a, **_k: pytest.fail('发出了请求'))


def test_missing_glossary_term_retries_once():
    calls = []
    def post(*_a, **kwargs):
        calls.append(kwargs['json'])
        return Response('模型已发布。' if len(calls) == 1 else 'Claude Sonnet 5.5 已发布。')
    assert tr.translate_to_chinese('Claude Sonnet 5.5 was released.', post) == 'Claude Sonnet 5.5 已发布。'
    assert len(calls) == 2 and 'Claude Sonnet 5.5' in calls[1]['messages'][0]['content']


def test_persistent_term_loss_warns_without_rejecting():
    events = []
    calls = []
    def post(*_a, **_k):
        calls.append(1)
        return Response('模型已发布。')
    assert tr.translate_to_chinese('Claude Sonnet 5.5 was released.', post,
                                   on_event=lambda *args: events.append(args)) == '模型已发布。'
    assert len(calls) == 2 and any(kind == 'warning' for kind, _ in events)


@pytest.mark.parametrize('returned', ['The model was released.', 'No Chinese words here.'])
def test_invalid_translation_raises(returned):
    with pytest.raises(ValueError, match='有效中文'):
        tr.translate_to_chinese('The model was released.', lambda *_a, **_k: Response(returned))


def test_long_text_uses_1200_character_chunks():
    chunks = []
    def post(*_a, **kwargs):
        chunks.append(kwargs['json']['messages'][1]['content'])
        return Response('译文。')
    tr.translate_to_chinese('word ' * 600, post)
    assert len(chunks) > 1 and all(len(chunk) <= 1200 for chunk in chunks)


def test_direct_session_ignores_environment_proxy(monkeypatch):
    sessions = []
    class Session:
        def __init__(self):
            self.trust_env = True
            sessions.append(self)
        def post(self, *_a, **_k):
            assert self.trust_env is False
            return Response('模型已发布。')
        def close(self):
            pass
    monkeypatch.setattr(tr.requests, 'Session', Session)
    assert tr.translate_to_chinese('The model was released.') == '模型已发布。'
    assert sessions[0].trust_env is False


def test_direct_failure_tries_environment_proxy(monkeypatch):
    sessions = []
    class Session:
        def __init__(self):
            self.trust_env = True
            sessions.append(self)
        def post(self, *_a, **_k):
            if not self.trust_env:
                raise requests.ConnectionError('直连失败')
            return Response('模型已发布。')
        def close(self):
            pass
    monkeypatch.setattr(tr.requests, 'Session', Session)
    assert tr.translate_to_chinese('The model was released.') == '模型已发布。'
    assert len(sessions) == 2 and sessions[1].trust_env is True


def test_cache_evicts_oldest_entry():
    cache = {f'{index:064x}': {'zh': '译文', 'model': 'deepseek-chat',
             'ts': f'2026-09-{index % 28 + 1:02d}T00:00:00+00:00'} for index in range(5001)}
    cache['oldest'] = {'zh': '旧译文', 'model': 'deepseek-chat',
                       'ts': '2020-01-01T00:00:00+00:00'}
    tr._save_translation_cache(cache)
    stored = json.loads(tr.CACHE_PATH.read_text(encoding='utf-8'))
    assert len(stored) == 5000 and 'oldest' not in stored
