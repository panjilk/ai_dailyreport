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
