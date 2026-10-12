"""Evidence and subprocess boundaries for the vendored multi-source collector."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from dailyreport import tech_digest
from dailyreport.recency import SHANGHAI


NOW = datetime(2026, 10, 12, 20, tzinfo=SHANGHAI)
RECENT = '2026-10-12T08:00:00Z'


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def article(channel='rss', **values):
    return dict({'title': 'Gemini model release', 'date': RECENT,
                 'link': 'https://blog.google/technology/ai/gemini-new/',
                 'topics': ['llm'], 'source_type': channel, 'source_id': 'google',
                 'source_name': 'Google AI', 'snippet': 'Search/feed snippet only.'}, **values)


@pytest.fixture
def setup_digest(tmp_path, monkeypatch):
    root = tmp_path / '中文项目'
    monkeypatch.setattr(tech_digest, 'ROOT', root)
    for key in tech_digest.SECRET_KEYS:
        monkeypatch.delenv(key, raising=False)
    skill = root / 'vendor' / 'tech-news-digest'
    (skill / 'scripts').mkdir(parents=True)
    (skill / 'scripts' / 'run-pipeline.py').write_text('# test pipeline', encoding='utf-8')
    defaults = root / 'config' / 'tech-news-digest'
    save(defaults / 'sources.json', {'sources': [
        {'id': 'google', 'type': 'rss', 'enabled': True, 'official': True,
         'topics': ['llm'], 'name': 'Google AI'},
        {'id': 'tibo', 'type': 'twitter', 'enabled': True,
         'topics': ['llm'], 'name': 'Tibo'},
        {'id': 'transformers', 'type': 'github', 'enabled': True,
         'topics': ['llm'], 'name': 'Transformers'}]})
    save(defaults / 'topics.json', {'topics': [{'id': 'llm'}, {'id': 'ai-agent'}]})
    config = {'tech_news_digest': {'enabled': True,
              'skill_dir': 'vendor/tech-news-digest', 'defaults_dir': 'config/tech-news-digest',
              'step_timeout_seconds': 90}}
    return root, config, root / 'outputs' / '本次采集'


def runner(*, merged=None, raw=None, returncode=0, states=None):
    """Write the same output/meta/intermediate paths used by run-pipeline.py."""
    calls = []

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        output = Path(command[command.index('--output') + 1])
        raw_dir = Path(command[command.index('--reuse-dir') + 1])
        active = command[command.index('--only') + 1].split(',')
        names = {'rss': 'RSS', 'github': 'GitHub', 'twitter': 'Twitter', 'web': 'Web'}
        for channel in active:
            save(raw_dir / (channel + '.json'), (raw or {}).get(channel, {
                'sources' if channel != 'web' else 'topics': [], 'total_articles': 0}))
        save(output, merged or {'topics': {}})
        save(output.with_suffix('.meta.json'), {'steps': [
            {'name': names[channel], 'status': (states or {}).get(channel, 'ok')}
            for channel in active], 'merge': {'status': 'ok'}})
        return SimpleNamespace(returncode=returncode, stdout='ignored', stderr='ignored')

    return execute, calls


def test_no_keys_runs_only_free_layers_and_preserves_parent_environment(setup_digest, monkeypatch):
    root, config, work = setup_digest
    execute, calls = runner()
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    before = dict(os.environ)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    command, arguments = calls[0]
    assert command[command.index('--only') + 1] == 'rss,github'
    assert command[command.index('--skip') + 1] == 'trending,reddit'
    assert arguments['shell'] is False
    assert arguments['encoding'] == 'utf-8'
    assert arguments['env']['PYTHONUTF8'] == '1'
    assert arguments['env']['PYTHONIOENCODING'] == 'utf-8'
    assert arguments['env']['TECH_NEWS_DIGEST_STATE_DIR'] == str(root / 'outputs' / '.tech-news-digest-state')
    assert dict(os.environ) == before
    assert arguments['cwd'] == str(root)
    assert any('中文项目' in item for item in command)
    assert result['status']['layers']['twitter']['state'] == 'skipped_missing_credentials'
    assert result['status']['layers']['web']['state'] == 'skipped_missing_credentials'
    assert result['status']['state'] == 'ok'


def test_article_requires_original_body_and_chinese_uses_normal_gate(setup_digest, monkeypatch):
    _, config, work = setup_digest
    execute, _ = runner(merged={'topics': {'llm': {'articles': [
        article(), article(title='Gemini 发布新模型', link='https://blog.google/zh/model')
    ]}}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    rows = tech_digest.collect_digest(config, NOW, 120, work)['rows']
    assert len(rows) == 2
    assert rows[0]['content_kind'] == 'official_article'
    assert rows[0]['requires_full_article'] is True
    assert rows[0]['abstract'] == 'Search/feed snippet only.'
    assert rows[0]['event_date'] == rows[0]['published']
    assert '仅证明发表日期' in rows[0]['event_date_evidence']
    assert rows[0]['original_article']['date'] == RECENT
    assert rows[0]['collection_backend'] == 'tech-news-digest'
    assert 'content_kind' not in rows[1]


def test_timestamp_window_timezone_and_url_validation(setup_digest, monkeypatch):
    _, config, work = setup_digest
    candidates = [
        article(title='cutoff accepted', date='2026-10-07T16:00:00Z', link='https://example.com/start'),
        article(title='old UTC but recent Beijing', date='2026-10-07T17:00:00Z', link='https://example.com/recent'),
        article(date='2026-10-07T15:59:59Z', link='https://example.com/old'),
        article(date='2026-10-12T20:01:00+08:00', link='https://example.com/future'),
        article(date='2026-10-12T10:00:00', link='https://example.com/naive'),
        article(date='2026-10-12', link='https://example.com/date-only'),
        article(link='javascript:alert(1)'), article(link='https://user:pass@example.com/story'),
        article(link='http://127.0.0.1/admin'), article(link='https://example.com:99999/story'),
        article(topics=['crypto'], link='https://example.com/crypto')]
    execute, _ = runner(merged={'topics': {'llm': {'articles': candidates}}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert [row['title'] for row in result['rows']] == ['cutoff accepted', 'old UTC but recent Beijing']
    assert result['status']['rejected'] == {'irrelevant_topic': 1, 'invalid_url': 4,
                                           'invalid_date': 2, 'outside_window': 2}


def test_requested_hours_can_be_narrower_than_five_day_window(setup_digest, monkeypatch):
    _, config, work = setup_digest
    execute, _ = runner(merged={'topics': {'llm': {'articles': [article(date='2026-10-11T11:00:00Z')]}}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 24, work)
    assert not result['rows']
    assert result['status']['rejected']['outside_window'] == 1


def test_raw_twitter_survives_cross_channel_merge_and_is_never_formal_news(setup_digest, monkeypatch):
    _, config, work = setup_digest
    monkeypatch.setenv('X_BEARER_TOKEN', 'test-twitter-secret-12345')
    post = article(channel='twitter', title='Should Codex limits be reset? Vote below.',
                   link='https://twitter.com/thsottiaux/status/123',
                   poll={'options': ['Yes', 'No']}, source_id='tibo')
    raw = {'twitter': {'sources': [{'source_id': 'tibo', 'name': 'Tibo', 'handle': 'thsottiaux',
                                   'status': 'ok', 'topics': ['llm'], 'articles': [post]}]}}
    execute, calls = runner(merged={'topics': {'llm': {'articles': [
        article(link='https://x.com/thsottiaux/status/123?utm_source=digest')
    ]}}}, raw=raw)
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert 'twitter' in calls[0][0][calls[0][0].index('--only') + 1]
    assert result['rows'] == []
    assert len(result['pending']) == 1
    post = result['pending'][0]
    assert post['account'] == 'thsottiaux'
    assert post['content_kind'] == 'social_post'
    assert post['review_status'] == 'pending'
    assert post['claim_status'] == 'unverified_social_statement'
    assert post['poll']['options'] == ['Yes', 'No']
    assert 'Vote below.' in post['source_text']
    assert 'event_date' in post['pending_fields']


def test_web_snippet_and_missing_social_dates_remain_review_leads(setup_digest, monkeypatch):
    _, config, work = setup_digest
    execute, _ = runner(merged={'topics': {'llm': {'articles': [
        article(channel='web', date='', link='https://example.com/search-hit'),
        article(channel='twitter', date='2026-10-12T08:00:00', link='https://x.com/person/status/5')
    ]}}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert not result['rows']
    assert len(result['pending']) == 2
    assert all(row['published'] == '' for row in result['pending'])
    assert all('publication_time' in row['pending_fields'] for row in result['pending'])
    assert all(row['discovered_at'] == NOW.isoformat() for row in result['pending'])


def test_only_complete_stable_release_notes_are_formal_rows(setup_digest, monkeypatch):
    _, config, work = setup_digest
    release = article(channel='github', source_id='transformers',
                      title='Transformers v5.0.0', link='https://github.com/huggingface/transformers/releases/tag/v5.0.0',
                      published_at=RECENT, body='Full original release notes. Adds model support.',
                      draft=False, prerelease=False)
    candidates = [release, dict(release, body='', link=release['link'] + '-no-notes'),
                  dict(release, prerelease=True, link=release['link'] + '-beta1'),
                  dict(release, link=release['link'] + '-rc1'),
                  article(channel='github', link=release['link'] + '-atom')]
    execute, _ = runner(merged={'topics': {'llm': {'articles': candidates}}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert len(result['rows']) == 1
    assert result['rows'][0]['content_kind'] == 'release'
    assert result['rows'][0]['abstract'] == release['body']
    assert len(result['pending']) == 4
    assert all(row['content_kind'] == 'github_candidate' for row in result['pending'])


def test_nonzero_partial_failure_keeps_successful_rss_rows(setup_digest, monkeypatch):
    _, config, work = setup_digest
    raw = {'rss': {'sources': [{'status': 'ok', 'articles': [article()]}], 'total_articles': 1}}
    execute, _ = runner(merged={'topics': {'llm': {'articles': [article()]}}},
                        raw=raw, returncode=1, states={'github': 'error'})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert len(result['rows']) == 1
    assert result['status']['state'] == 'partial'
    assert result['status']['layers']['github']['state'] == 'failed'
    assert result['errors']


def test_all_fetch_failures_are_not_reported_as_no_news(setup_digest, monkeypatch):
    _, config, work = setup_digest
    execute, _ = runner(returncode=1, states={'rss': 'error', 'github': 'timeout'})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert result['status']['state'] == 'failed'
    assert len(result['errors']) == 2


def test_missing_and_non_model_profiles_fail_before_pipeline(setup_digest, monkeypatch):
    root, config, work = setup_digest
    execute, calls = runner()
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    config['tech_news_digest']['defaults_dir'] = 'config/missing'
    assert tech_digest.collect_digest(config, NOW, 120, work)['status']['state'] == 'failed'
    config['tech_news_digest']['defaults_dir'] = 'config/tech-news-digest'
    save(root / 'config' / 'tech-news-digest' / 'topics.json', {'topics': [{'id': 'crypto'}]})
    assert tech_digest.collect_digest(config, NOW, 120, work)['status']['state'] == 'failed'
    assert calls == []


def test_secret_values_redacted_from_raw_meta_and_returned_records(setup_digest, monkeypatch):
    _, config, work = setup_digest
    secret = 'sensitive-twitter-key-987654321'
    monkeypatch.setenv('TWITTERAPI_IO_KEY', secret)
    monkeypatch.setenv('TAVILY_API_KEY', 'sensitive-search-key-987654321')
    execute, calls = runner(raw={'twitter': {'sources': [{'status': 'error', 'error': 'key=' + secret}]}})
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    active = calls[0][0][calls[0][0].index('--only') + 1]
    assert 'twitter' in active and 'web' in active
    assert secret not in json.dumps(result)
    assert all(secret not in path.read_text(encoding='utf-8') for path in work.rglob('*.json'))
    assert os.environ['TWITTERAPI_IO_KEY'] == secret


def test_process_timeout_has_safe_error_and_does_not_expose_stderr(setup_digest, monkeypatch):
    _, config, work = setup_digest
    def execute(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 210, stderr='secret token in stderr')
    monkeypatch.setattr(tech_digest.subprocess, 'run', execute)
    result = tech_digest.collect_digest(config, NOW, 120, work)
    assert result['status']['state'] == 'failed'
    assert 'secret token' not in json.dumps(result)


def test_disabled_backend_does_not_launch_or_create_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(tech_digest.subprocess, 'run', lambda *_args, **_kwargs: pytest.fail('must not launch'))
    work = tmp_path / 'unused'
    assert tech_digest.collect_digest({}, NOW, 120, work)['status']['state'] == 'disabled'
    assert not work.exists()
