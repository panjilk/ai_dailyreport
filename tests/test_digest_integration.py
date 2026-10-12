"""Exercise the actual evidence gate and default CLI integration, without APIs."""
import json
from datetime import datetime

import pytest

from dailyreport.collect import collect
from dailyreport.recency import SHANGHAI


NOW = datetime(2026, 10, 12, 18, tzinfo=SHANGHAI)
PUBLISHED = '2026-10-12T08:00:00Z'
TITLE = 'Gemini model update released'
BODY = ('Today Google released a Gemini model update with an API for developers. '
        'The Gemini model supports text processing and provides new tools for developers.')
SOURCE = 'https://example.com/news/gemini'


def english_row():
    return dict(title=TITLE, published=PUBLISHED, source_url=SOURCE,
                source_name='Google Gemini', content_kind='official_article',
                abstract='A feed snippet makes an unsupported claim.',
                event_date=PUBLISHED, event_date_evidence='RSS publication time only',
                requires_full_article=True, collection_backend='tech-news-digest')


def translate(text):
    if text == TITLE:
        return 'Gemini 新模型发布'
    if text.startswith('Today Google'):
        return '今天，Google 发布 Gemini 新模型，为开发者提供新的 API 工具。'
    if 'supports text' in text:
        return 'Gemini 模型支持文本处理，并为开发者提供新的工具。'
    if text.startswith('Today Anthropic'):
        return '今天，Anthropic 发布 Claude 模型更新，为开发者提供新的 API 工具。'
    return '9月10日，Google 发布 Gemini 模型，为开发者提供新的 API 工具。'


def test_supplement_fetches_original_and_replaces_rss_event_placeholder(monkeypatch):
    calls = []
    monkeypatch.setattr('dailyreport.collect._fetch', lambda url: calls.append(url) or
                        '<article><p>' + BODY + '</p></article>')
    monkeypatch.setattr('dailyreport.collect.translate_to_chinese', translate)
    result = collect({'sources': [], 'topic_scope': 'all_ai', 'require_concrete_news': True},
                     NOW, 120, 5, extra_rows=[english_row()])
    story = result['stories'][0]
    assert calls == [SOURCE]
    assert result['collection_stats']['article_requests'] == 1
    assert story['source_text'] == BODY
    assert story['event_date'] == '2026-10-12'
    assert '今天' in story['event_date_evidence']
    assert 'unsupported claim' not in story['narration']


def test_supplement_cannot_use_feed_snippet_when_original_has_no_body(monkeypatch):
    monkeypatch.setattr('dailyreport.collect._fetch', lambda url: '<html><p>Navigation</p></html>')
    with pytest.raises(RuntimeError, match='英文原文缺少'):
        collect({'sources': [], 'topic_scope': 'all_ai'}, NOW, 120, 5,
                extra_rows=[english_row()])


def test_new_rss_publication_cannot_refresh_old_event(monkeypatch):
    monkeypatch.setattr('dailyreport.collect._fetch', lambda url:
                        '<article><p>On September 10, Google released a Gemini model with new API tools for developers.</p></article>')
    monkeypatch.setattr('dailyreport.collect.translate_to_chinese', translate)
    with pytest.raises(RuntimeError, match='原文事件不在本次搜查窗口'):
        collect({'sources': [], 'topic_scope': 'all_ai'}, NOW, 120, 5,
                extra_rows=[english_row()])


def test_official_html_articles_count_against_body_budget(monkeypatch):
    index = '<main><a href="/news/a">Claude update</a><a href="/news/b">Claude second update</a></main>'
    html = ('<meta property="og:title" content="Claude model update">'
            '<meta property="article:published_time" content="2026-10-12T08:00:00Z">'
            '<article><p>Today Anthropic released a Claude model update with an API for developers. '
            'The Claude model supports text processing and provides new tools for developers. '
            'The announcement includes documentation for the new model and developer tools.</p></article>')
    calls = []
    monkeypatch.setattr('dailyreport.collect._fetch', lambda url: calls.append(url) or
                        (index if url.endswith('/news') else html))
    monkeypatch.setattr('dailyreport.collect.translate_to_chinese',
                        lambda text: 'Claude 新模型发布' if text == 'Claude model update' else translate(text))
    config = {'topic_scope': 'all_ai', 'article_request_budget': 1,
              'sources': [{'name': 'Anthropic', 'url': 'https://www.anthropic.com/news',
                           'type': 'official_html_index'}]}
    result = collect(config, NOW, 120, 5)
    assert result['collection_stats']['article_requests'] == 1
    assert len(calls) == 2
    assert len(result['stories']) == 1
    assert result['stories'][0]['event_date'] == '2026-10-12'


def test_default_cli_runs_digest_then_quality_collector_and_exports_review(tmp_path, monkeypatch):
    import dailyreport.__main__ as cli

    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'tech_news_digest': {'enabled': True}}), encoding='utf-8')
    output = tmp_path / 'edition'
    pending = [{'title': 'Tibo poll', 'review_status': 'pending', 'account': 'thsottiaux'}]
    status = {'state': 'ok', 'layers': {'twitter': {'state': 'skipped_missing_credentials'}}}
    calls = []

    def digest(settings, now, hours, work_dir):
        calls.append(('digest', work_dir))
        return {'rows': [english_row()], 'pending': pending, 'errors': [], 'status': status}

    def collector(settings, now, hours, limit, **kwargs):
        calls.append(('collect', kwargs))
        today = now.astimezone(SHANGHAI).date().isoformat()
        return {'date': today, 'stories': [
            {'title': 'Gemini 新模型发布', 'published': today, 'event_date': today,
             'category': '模型发布', 'bullets': ['Google 发布 Gemini 新模型，支持 API 工具。'],
             'narration': 'Google 发布 Gemini 新模型，支持 API 工具。',
             'source_url': SOURCE, 'source_name': 'Google Gemini'}]}

    monkeypatch.setattr(cli, 'collect_digest', digest)
    monkeypatch.setattr(cli, 'collect', collector)
    assert cli.main(['--config', str(config), '--output', str(output), '--collect-only']) == 0
    assert calls[0] == ('digest', output / 'tech-news-digest')
    assert calls[1][1]['extra_rows'] == [english_row()]
    assert json.loads((output / 'collection-status.json').read_text('utf-8')) == status
    assert json.loads((output / 'review-candidates.json').read_text('utf-8')) == pending
    assert len(json.loads((output / 'briefing.json').read_text('utf-8'))['stories']) == 1
    assert not (output / 'daily.mp4').exists()


def test_enabled_digest_does_not_overwrite_existing_collection(tmp_path, monkeypatch):
    import dailyreport.__main__ as cli
    config = tmp_path / 'config.json'
    config.write_text('{"tech_news_digest": {"enabled": true}}', encoding='utf-8')
    output = tmp_path / 'edition'
    (output / 'tech-news-digest').mkdir(parents=True)
    monkeypatch.setattr(cli, 'collect_digest', lambda *args: pytest.fail('should stop before network'))
    assert cli.main(['--config', str(config), '--output', str(output), '--collect-only']) == 1
