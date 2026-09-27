import json
from datetime import datetime
from unittest.mock import patch

import pytest

from dailyreport.collect import collect
from dailyreport.international import (english_ai_related, english_blog_candidate,
                                       english_summary, english_topic, paper_details,
                                       source_rows, translate_to_chinese)
from dailyreport.recency import SHANGHAI

NOW = datetime(2026, 9, 14, 20, tzinfo=SHANGHAI)
ABSTRACT = 'We introduce a language model for reasoning. Results improve accuracy on a public benchmark. However, evaluation is limited to English tasks.'


def chinese_translation(_text):
    return '中文机器翻译内容。'


def paper_page(day='13 Sep 2026'):
    return '<div class="submission-history"><strong>[v1]</strong> Sun, ' + day + ' 10:00:00 UTC (10 KB)<br/>[v2] Mon, 14 Sep 2026 10:00:00 UTC</div><meta name="citation_abstract" content="' + ABSTRACT + '">'


def test_first_submission_is_used_instead_of_revision():
    text, event = paper_details(paper_page())
    assert text == ABSTRACT
    assert event['event_date'] == '2026-09-13T10:00:00+00:00'
    with pytest.raises(ValueError, match='首次提交'):
        paper_details('<meta name="citation_date" content="2026/09/14">')


def test_hf_recommendation_does_not_refresh_paper():
    rows = list(source_rows({'type': 'hf_papers'}, json.dumps([{
        'publishedAt': '2026-09-14T10:00:00Z', 'paper': {'id': '2609.12345', 'title': 'LLM Evaluation',
        'publishedAt': '2026-09-01T10:00:00Z', 'summary': ABSTRACT}}])))
    assert rows[0]['published'] == '2026-09-01T10:00:00Z'
    assert rows[0]['source_url'] == 'https://arxiv.org/abs/2609.12345'


def test_english_summary_keeps_claims_and_limitations():
    bullets = english_summary(ABSTRACT, 'paper')
    assert '作者报告' in bullets[0]
    assert 'However, evaluation is limited to English tasks.' in bullets
    assert all(s in ABSTRACT for s in bullets[1:])
    assert english_topic('Research', ABSTRACT)
    assert not english_topic('Quarterly earnings', 'Revenue increases.')
    with pytest.raises(ValueError, match='截断文字'):
        english_summary('This AI release promises several improvements... However, details are limited.', 'article')


def test_release_date_and_stable_only():
    entry = dict(tag_name='v5.0', html_url='https://github.com/a/b/releases/tag/v5.0',
                 published_at='2026-09-13T10:00:00Z', updated_at='2026-09-14T10:00:00Z', body=ABSTRACT)
    rows = list(source_rows({'type': 'github_releases', 'name': 'Transformers'}, json.dumps([
        entry, dict(entry, draft=True), dict(entry, prerelease=True)])))
    assert len(rows) == 1
    assert rows[0]['event_date'] == entry['published_at']


def test_official_changelog_extracts_dated_model_release_once():
    url = 'https://longcat.chat/platform/docs/ChangeLog.html'
    html = '''<h2>Version: 2026-09-25</h2>
    <h3 id="longcat-new">LongCat-2.5-Preview Now Available</h3>
    <p>LongCat-2.5-Preview adds image understanding and coding capabilities.</p>
    <ul><li>Supports visual reasoning and cross-modal questions.</li></ul>
    <h2>Version: 2026-09-25</h2>
    <h3>LongCat-2.5-Preview Now Available</h3>
    <p>LongCat-2.5-Preview adds image understanding and coding capabilities.</p>
    <h2>Version: 2026-09-10</h2><h3>Enterprise Services</h3><p>Billing changes.</p>'''
    rows = list(source_rows({'type': 'official_changelog', 'url': url}, html))
    assert len(rows) == 1
    assert rows[0]['event_date'] == '2026-09-25T12:00:00+08:00'
    assert rows[0]['source_url'].endswith('#longcat-new')
    assert 'visual reasoning' in rows[0]['abstract']


@patch('dailyreport.collect.translate_to_chinese', side_effect=chinese_translation)
@patch('dailyreport.collect._fetch')
def test_english_paper_reaches_briefing_without_chinese_regex(fetch, _translate):
    feed = json.dumps([{'paper': {'id': '2609.12345', 'title': 'LLM Reasoning',
                       'publishedAt': '2026-09-13T10:00:00Z', 'summary': ABSTRACT}}])
    fetch.side_effect = [feed, paper_page()]
    result = collect({'sources': [{'name': 'HF', 'url': 'https://huggingface.co/api/daily_papers', 'type': 'hf_papers'}]}, NOW, 48, 1)
    story = result['stories'][0]
    assert story['language'] == 'zh'
    assert story['source_language'] == 'en'
    assert story['title'] == '中文机器翻译内容。'
    assert all(not any('a' <= char.lower() <= 'z' for char in bullet) for bullet in story['bullets'])
    assert story['category'] == '技术洞察'
    assert story['source_text'] == ABSTRACT
    assert story['event_date'].startswith('2026-09-13')
    assert result['collection_stats']['selected'] == 1
    from dailyreport.render import single_page_layout, validate_briefing
    single_page_layout(story)
    validate_briefing(result)


@patch('dailyreport.collect._fetch')
def test_recent_hf_entry_with_old_first_submission_is_rejected(fetch):
    feed = json.dumps([{'paper': {'id': '2609.12345', 'title': 'LLM Reasoning',
                       'publishedAt': '2026-09-14T10:00:00Z', 'summary': ABSTRACT}}])
    fetch.side_effect = [feed, paper_page('01 Sep 2026')]
    with pytest.raises(RuntimeError, match='首次提交'):
        collect({'sources': [{'name': 'HF', 'url': 'https://huggingface.co/api/daily_papers', 'type': 'hf_papers'}]}, NOW, 48, 1)


@patch('dailyreport.collect.translate_to_chinese', side_effect=chinese_translation)
@patch('dailyreport.collect._fetch')
def test_release_reaches_briefing_without_article_fetch(fetch, _translate):
    fetch.return_value = json.dumps([dict(tag_name='v5.0', html_url='https://github.com/a/b/releases/tag/v5.0',
                                       published_at='2026-09-13T10:00:00Z', body=ABSTRACT)])
    result = collect({'sources': [{'name': 'Transformers', 'url': 'https://api.github.com/repos/a/b/releases', 'type': 'github_releases'}]}, NOW, 48, 1)
    assert result['stories'][0]['category'] == '开发生态'
    assert fetch.call_count == 1
    assert result['collection_stats']['article_requests'] == 0


@patch('dailyreport.collect.translate_to_chinese', side_effect=chinese_translation)
@patch('dailyreport.collect._fetch')
def test_release_with_empty_body_is_skipped_without_aborting_collection(fetch, _translate):
    fetch.return_value = json.dumps([
        dict(tag_name='v5.1', html_url='https://github.com/a/b/releases/tag/v5.1',
             published_at='2026-09-14T11:00:00Z', body=None),
        dict(tag_name='v5.0', html_url='https://github.com/a/b/releases/tag/v5.0',
             published_at='2026-09-14T10:00:00Z', body=ABSTRACT),
    ])
    result = collect({
        'topic_scope': 'all_ai',
        'sources': [{'name': 'Transformers', 'url': 'https://api.github.com/repos/a/b/releases',
                     'type': 'github_releases'}],
    }, NOW, 48, 1)
    assert result['stories'][0]['title'] == '中文机器翻译内容。'
    assert result['collection_stats']['summary_rejected'] == 1


def test_arxiv_replacements_are_not_new_papers():
    xml = '''<rss xmlns:arxiv="http://arxiv.org/schemas/atom"><channel>
    <item><title>LLM paper</title><link>https://arxiv.org/abs/2609.12345</link>
    <description>Abstract: language model evaluation.</description><arxiv:announce_type>replace</arxiv:announce_type></item>
    </channel></rss>'''
    assert list(source_rows({'type': 'arxiv'}, xml)) == []


def test_english_rss_uses_embedded_article_and_published_date():
    xml = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <title>New OpenAI agent tool</title><link href="https://example.com/agent" />
    <published>2026-09-14T10:00:00Z</published>
    <content type="html"><![CDATA[<p>OpenAI released a new AI agent tool for developers today.</p>
    <p>The update improves tool use reliability on public evaluations.</p>]]></content>
    </entry></feed>'''
    row = list(source_rows({'type': 'english_rss'}, xml))[0]
    assert row['content_kind'] == 'article'
    assert row['event_date'] == '2026-09-14T10:00:00+00:00'
    assert 'improves tool use reliability' in row['abstract']
    assert english_ai_related(row['title'], row['abstract'])
    assert not english_ai_related('Database indexing notes', 'A tutorial about B-trees and SQL queries.')
    assert english_blog_candidate('llm-keys-ui 0.1', 'A small plugin for LLM API keys.')
    assert not english_blog_candidate('Quoting voxium', 'A short quotation about LLM deployment.')
    assert not english_blog_candidate('Note on 18th September 2026', 'A note about LLM research.')
    assert english_blog_candidate('Why Dario Amodei changed his AI safety position', 'Anthropic policy analysis.')


def test_english_rss_normalizes_rfc822_date_for_recency_checks():
    xml = '''<rss><channel><item><title>AI systems update</title>
    <link>https://example.com/ai</link><pubDate>Sun, 20 Sep 2026 00:00:00 GMT</pubDate>
    <description>Artificial intelligence systems are changing software development.</description>
    </item></channel></rss>'''
    row = list(source_rows({'type': 'english_rss'}, xml))[0]
    assert row['published'] == '2026-09-20T00:00:00+00:00'
    assert row['event_date'] == row['published']


def test_official_english_feed_keeps_official_role_and_notice():
    xml = '''<rss><channel><item><title>New AI model</title>
    <link>https://example.com/model</link><pubDate>Mon, 21 Sep 2026 12:00:00 GMT</pubDate>
    <description>We released a new AI model for developers. Results improve accuracy on a public benchmark.</description>
    </item></channel></rss>'''
    row = list(source_rows({'type': 'english_rss', 'content_kind': 'official_article'}, xml))[0]
    assert row['content_kind'] == 'official_article'
    assert english_summary(row['abstract'], row['content_kind'])[0].startswith('官方公告原文摘录')


@patch('dailyreport.collect.translate_to_chinese', side_effect=chinese_translation)
@patch('dailyreport.collect._fetch')
def test_english_rss_filters_non_ai_posts_and_needs_no_article_request(fetch, _translate):
    fetch.return_value = '''<rss><channel>
    <item><title>Database indexing notes</title><link>https://example.com/sql</link>
    <pubDate>2026-09-14T11:00:00Z</pubDate><description>A tutorial about B-trees and SQL queries.</description></item>
    <item><title>New OpenAI agent tool</title><link>https://example.com/agent</link>
    <pubDate>2026-09-14T10:00:00Z</pubDate><description>
    OpenAI released a new AI agent tool for developers today. The update improves tool use reliability on public evaluations. However, the initial release is limited to selected accounts.
    </description></item></channel></rss>'''
    result = collect({'topic_scope': 'all_ai', 'sources': [{
        'name': 'AI Blog', 'url': 'https://example.com/feed',
        'type': 'english_rss', 'ai_only': False,
    }]}, NOW, 48, 1)
    story = result['stories'][0]
    assert story['title'] == '中文机器翻译内容。'
    assert story['content_kind'] == 'article'
    assert story['category'] == '技术洞察'
    assert story['nav_label'] == 'OpenAI'
    assert result['collection_stats']['article_requests'] == 0
    assert result['collection_stats']['off_topic'] == 1


def test_translation_service_returns_chinese_and_rejects_english_fallback():
    class Response:
        def __init__(self, translated):
            self.translated = translated
        def raise_for_status(self):
            return None
        def json(self):
            return {'responseData': {'translatedText': self.translated}, 'responseStatus': 200}

    def success(_url, **_kwargs):
        return Response('人工智能安全讨论仍需要完整证据。')

    assert translate_to_chinese('AI safety still needs evidence.', success) == '人工智能安全讨论仍需要完整证据。'
    with pytest.raises(ValueError, match='有效中文'):
        translate_to_chinese('AI safety still needs evidence.', lambda *_args, **_kwargs: Response('AI safety still needs evidence.'))
