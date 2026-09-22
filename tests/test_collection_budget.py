from datetime import datetime
from unittest.mock import patch

import pytest

from dailyreport.collect import collect, extract_paragraphs, select_recent
from dailyreport.recency import SHANGHAI

NOW = datetime(2026, 9, 12, 16, tzinfo=SHANGHAI)
TEXT = '研究团队今天发布DeepSeek新模型。模型支持中文文本处理，能够完成复杂推理任务。'


def feed(count):
    return '<rss><channel>' + ''.join(
        f'<item><title>DeepSeek 模型发布 {i}</title><link>https://example.com/{i}</link>'
        '<pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate></item>' for i in range(count)
    ) + '</channel></rss>'


def config(budget=40):
    return {'article_request_budget': budget, 'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}


@patch('dailyreport.collect._fetch')
def test_keeps_searching_past_twenty_rejected_candidates(fetch):
    def response(url):
        if url.endswith('rss'):
            return feed(25)
        if int(url.rsplit('/', 1)[1]) < 22:
            raise OSError('timeout')
        return '<article><p>' + TEXT + '</p></article>'
    fetch.side_effect = response
    result = collect(config(), NOW, 48, 1)
    assert result['stories'][0]['source_url'].endswith('/22')
    assert result['collection_stats']['article_requests'] == 23
    assert result['collection_stats']['fetch_failures'] == 22
    assert result['collection_stats']['selected'] == 1
    assert not result['collection_stats']['budget_exhausted']


@patch('dailyreport.collect._fetch')
def test_request_budget_is_hard_limit_and_reports_exhaustion(fetch):
    def response(url):
        if url.endswith('rss'):
            return feed(25)
        if url.endswith('/0'):
            return '<article><p>' + TEXT + '</p></article>'
        raise OSError('timeout')
    fetch.side_effect = response
    result = collect(config(4), NOW, 48, 2)
    assert fetch.call_count == 5
    assert result['collection_stats']['budget_exhausted']
    assert result['collection_stats']['unexamined_candidates'] == 21


@patch('dailyreport.collect._fetch')
def test_atom_updated_requires_actual_event_evidence(fetch):
    atom = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <title>DeepSeek 新模型发布</title><link href="https://example.com/a"/>
    <updated>2026-09-12T10:00:00+08:00</updated></entry></feed>'''
    fetch.side_effect = [atom, '<article><p>' + TEXT + '</p></article>']
    assert collect(config(), NOW, 48, 1)['stories'][0]['event_date'] == '2026-09-12'
    fetch.side_effect = [atom, '<article><p>8月20日发布DeepSeek新模型。</p></article>']
    with pytest.raises(RuntimeError, match='date_rejected'):
        collect(config(), NOW, 48, 1)


@patch('dailyreport.collect._fetch')
def test_hourly_cutoff_rejects_older_event_and_continues_to_next_candidate(fetch):
    rss = '''<rss><channel>
    <item><title>DeepSeek 模型发布 旧事件</title><link>https://example.com/old</link>
    <pubDate>Sat, 12 Sep 2026 07:00:00 GMT</pubDate></item>
    <item><title>DeepSeek 模型发布 新事件</title><link>https://example.com/recent</link>
    <pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate></item>
    </channel></rss>'''

    def response(url):
        if url.endswith('/rss'):
            return rss
        if url.endswith('/old'):
            return '<article><p>9月10日研究团队发布DeepSeek新模型。模型支持中文文本处理，能够完成复杂推理任务。</p></article>'
        return '<article><p>9月12日研究团队发布DeepSeek新模型。模型支持中文文本处理，能够完成复杂推理任务。</p></article>'

    fetch.side_effect = response
    result = collect(config(), NOW, 24, 1)
    assert result['stories'][0]['source_url'] == 'https://example.com/recent'
    assert result['stories'][0]['event_date'] == '2026-09-12'
    assert result['collection_stats']['date_rejected'] == 1
    assert result['collection_stats']['article_requests'] == 2


def test_selection_diagnostics():
    def row(title, day, url):
        return dict(title=title, published=day, source_url=url)
    stats = {}
    rows = [row('A', '2026-09-12T10:00:00+08:00', 'https://e.com/a'),
            row('A', '2026-09-12T10:00:00+08:00', 'https://e.com/a'),
            row('old', '2026-09-10T10:00:00+08:00', 'https://e.com/b'),
            row('missing', None, 'https://e.com/c')]
    assert len(select_recent(rows, NOW, 48, 10, stats)) == 1
    assert stats == {'invalid_metadata': 1, 'outside_window': 1, 'duplicates': 1}


def test_qbit_article_container_excludes_sibling_content():
    html = '<div class="article"><p>' + TEXT + '</p></div><div class="content_right"><p>无关推荐内容。</p></div>'
    assert extract_paragraphs(html) == [TEXT]


@patch('dailyreport.collect._fetch')
def test_embedded_feed_content_avoids_article_request(fetch):
    embedded = '<p>9月12日研究团队发布DeepSeek新模型。</p><p>模型支持中文文本处理，能够完成复杂推理任务。</p>'
    fetch.return_value = ('<rss><channel><item><title>DeepSeek 模型发布</title>'
                          '<link>https://example.com/a</link><pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate>'
                          '<description><![CDATA[' + embedded + ']]></description></item></channel></rss>')
    result = collect({'sources': [{'name': '内嵌全文源', 'url': 'https://example.com/rss',
                                   'use_feed_content': True}]}, NOW, 120, 1)
    assert result['stories'][0]['source_text'].startswith('9月12日')
    assert result['collection_stats']['article_requests'] == 0
    assert fetch.call_count == 1


@patch('dailyreport.collect._fetch')
def test_per_source_cap_softly_refills_when_it_is_the_only_source(fetch):
    entries = ''.join(
        f'<item><title>DeepSeek 模型发布 {i}</title><link>https://example.com/{i}</link>'
        '<pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate></item>' for i in range(3))
    rss = '<rss><channel>' + entries + '</channel></rss>'
    fetch.side_effect = lambda url: rss if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
    result = collect({'sources': [{'name': '单一来源', 'url': 'https://example.com/rss', 'max_stories': 1}]}, NOW, 120, 3)
    assert [story['title'] for story in result['stories']] == [
        'DeepSeek 模型发布 0', 'DeepSeek 模型发布 1', 'DeepSeek 模型发布 2']
    assert result['collection_stats']['source_cap_skipped'] == 2
    assert result['collection_stats']['article_requests'] == 3


@patch('dailyreport.collect._fetch')
def test_per_source_cap_still_limits_when_other_sources_fill_limit(fetch):
    def source_feed(prefix):
        entries = ''.join(
            f'<item><title>DeepSeek 模型发布 {prefix}{i}</title>'
            f'<link>https://example.com/{prefix}/{i}</link>'
            '<pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate></item>' for i in range(2))
        return '<rss><channel>' + entries + '</channel></rss>'

    def response(url):
        if url.endswith('/a/rss'):
            return source_feed('a')
        if url.endswith('/b/rss'):
            return source_feed('b')
        return '<article><p>' + TEXT + '</p></article>'

    fetch.side_effect = response
    result = collect({'sources': [
        {'name': '来源A', 'url': 'https://example.com/a/rss', 'max_stories': 1},
        {'name': '来源B', 'url': 'https://example.com/b/rss', 'max_stories': 1},
    ]}, NOW, 120, 2)
    assert [story['source_name'] for story in result['stories']] == ['来源A', '来源B']
    assert result['collection_stats']['source_cap_skipped'] == 1
    assert result['collection_stats']['article_requests'] == 2


@patch('dailyreport.collect._fetch')
def test_source_cap_refills_in_global_order_when_another_source_fails(fetch):
    def source_feed(entries):
        return '<rss><channel>' + ''.join(
            f'<item><title>{title}</title><link>{url}</link><pubDate>{published}</pubDate></item>'
            for title, url, published in entries) + '</channel></rss>'

    feeds = {
        'https://example.com/a/rss': source_feed([
            ('DeepSeek 模型发布 A0', 'https://example.com/a/0', 'Sat, 12 Sep 2026 07:00:00 GMT'),
            ('DeepSeek 模型发布 A1', 'https://example.com/a/1', 'Sat, 12 Sep 2026 06:00:00 GMT'),
        ]),
        'https://example.com/b/rss': source_feed([
            ('DeepSeek 模型发布 B0', 'https://example.com/b/0', 'Sat, 12 Sep 2026 05:00:00 GMT'),
        ]),
        'https://example.com/c/rss': source_feed([
            ('DeepSeek 模型发布 C0', 'https://example.com/c/0', 'Sat, 12 Sep 2026 04:00:00 GMT'),
        ]),
    }

    def response(url):
        if url in feeds:
            return feeds[url]
        if url == 'https://example.com/c/0':
            raise OSError('timeout')
        return '<article><p>' + TEXT + '</p></article>'

    fetch.side_effect = response
    result = collect({'sources': [
        {'name': '来源A', 'url': 'https://example.com/a/rss', 'max_stories': 1},
        {'name': '来源B', 'url': 'https://example.com/b/rss', 'max_stories': 1},
        {'name': '来源C', 'url': 'https://example.com/c/rss', 'max_stories': 1},
    ]}, NOW, 120, 3)
    assert [story['title'] for story in result['stories']] == [
        'DeepSeek 模型发布 A0', 'DeepSeek 模型发布 A1', 'DeepSeek 模型发布 B0']
    assert result['collection_stats']['source_cap_skipped'] == 1
    assert result['collection_stats']['fetch_failures'] == 1
    assert result['collection_stats']['article_requests'] == 4


@patch('dailyreport.collect.translate_to_chinese', return_value='模型工具五点零版本')
@patch('dailyreport.collect._fetch')
def test_budget_exhaustion_still_processes_feed_content_and_release(fetch, _translate):
    normal_feed = ('<rss><channel><item><title>DeepSeek 模型发布 请求版</title>'
                   '<link>https://example.com/article</link>'
                   '<pubDate>Sat, 12 Sep 2026 07:00:00 GMT</pubDate></item></channel></rss>')
    embedded = ('<p>9月12日智谱发布GLM新模型。</p>'
                '<p>模型支持中文文本处理，能够完成复杂推理任务。</p>')
    embedded_feed = ('<rss><channel><item><title>GLM 模型发布 内嵌版</title>'
                     '<link>https://example.com/embedded-article</link>'
                     '<pubDate>Sat, 12 Sep 2026 06:00:00 GMT</pubDate>'
                     '<description><![CDATA[' + embedded + ']]></description></item></channel></rss>')
    release_feed = '''[{"tag_name":"v5.0","html_url":"https://github.com/a/b/releases/tag/v5.0",
        "published_at":"2026-09-12T05:00:00Z",
        "body":"Transformers now supports faster language model inference across common production deployments. The release improves text generation throughput while preserving the documented API behavior."}]'''

    def response(url):
        if url == 'https://example.com/normal/rss':
            return normal_feed
        if url == 'https://example.com/embedded/rss':
            return embedded_feed
        if url == 'https://api.github.com/repos/a/b/releases':
            return release_feed
        if url == 'https://example.com/article':
            raise OSError('timeout')
        raise AssertionError('unexpected article request: ' + url)

    fetch.side_effect = response
    result = collect({'article_request_budget': 1, 'sources': [
        {'name': '请求源', 'url': 'https://example.com/normal/rss'},
        {'name': '内嵌源', 'url': 'https://example.com/embedded/rss', 'use_feed_content': True},
        {'name': 'Transformers', 'url': 'https://api.github.com/repos/a/b/releases',
         'type': 'github_releases'},
    ]}, NOW, 120, 2)
    assert [story['title'] for story in result['stories']] == [
        'GLM 模型发布 内嵌版', '模型工具五点零版本']
    assert result['collection_stats']['article_requests'] == 1
    assert result['collection_stats']['fetch_failures'] == 1
    assert fetch.call_count == 4
