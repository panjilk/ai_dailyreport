import json
from datetime import datetime, timezone

from dailyreport.broadcast_log import append_edition, recent_fingerprints, url_fingerprint
from dailyreport.collect import collect


def story(title, url):
    return {'title': title, 'source_url': url, 'nav_label': '模型'}


def test_fingerprint_normalizes_title_and_ignores_repost_url():
    assert url_fingerprint('https://a', '模型 发布！') == url_fingerprint('https://b', ' 模型发布! ')
    assert url_fingerprint('https://a', '模型发布') != url_fingerprint('https://a', '模型下线')


def test_append_reload_and_recent_editions(tmp_path):
    path = tmp_path / 'log.json'
    for day, title in [('2026-09-10', '旧闻'), ('2026-09-11', '第一条'),
                       ('2026-09-12', '第二条'), ('2026-09-13', '第三条')]:
        append_edition({'date': day, 'stories': [story(title, f'https://e.test/{day}')]}, path)
    rows = json.loads(path.read_text())
    assert len(rows) == 4
    assert rows[-1]['nav_label'] == '模型'
    fingerprints, urls, warnings = recent_fingerprints(path)
    assert not warnings
    assert len(fingerprints) == len(urls) == 3
    assert url_fingerprint('', '旧闻') not in fingerprints


def test_recent_filter_excludes_candidate(tmp_path, monkeypatch):
    path = tmp_path / 'log.json'
    append_edition({'date': '2026-09-10', 'stories': [story('DeepSeek 模型发布', 'https://old.test/a')]}, path)
    feed = ('<rss><channel><item><title>DeepSeek 模型发布</title>'
            '<link>https://new.test/a</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>'
            '<item><title>Claude 模型发布</title><link>https://new.test/b</link>'
            '<pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item></channel></rss>')
    monkeypatch.setattr('dailyreport.collect._fetch', lambda url: feed if url.endswith('rss') else
                        '<article><p>研究团队今天发布Claude新模型。模型支持中文文本处理，能够完成复杂推理任务。</p></article>')
    result = collect({'sources': [{'name': '测试', 'url': 'https://e.test/rss'}]},
                     datetime(2026, 9, 11, 12, tzinfo=timezone.utc), 48, 2, log_path=path)
    assert [s['title'] for s in result['stories']] == ['Claude 模型发布']
    assert result['recently_broadcast'] == [{'title': 'DeepSeek 模型发布',
                                              'source_url': 'https://new.test/a',
                                              'appeared_date': '2026-09-10'}]
    assert result['collection_stats']['skipped_recently_broadcast'] == 1


def test_missing_and_damaged_log_degrade(tmp_path):
    path = tmp_path / 'log.json'
    assert recent_fingerprints(path)[:2] == (set(), set())
    path.write_text('{broken')
    fingerprints, urls, warnings = recent_fingerprints(path)
    assert (fingerprints, urls) == (set(), set())
    assert warnings


def test_same_day_append_is_idempotent(tmp_path):
    path = tmp_path / 'log.json'
    edition = {'date': '2026-09-13', 'stories': [story('模型 发布', 'https://a')]}
    append_edition(edition, path)
    edition['stories'][0]['source_url'] = 'https://b'
    append_edition(edition, path)
    assert len(json.loads(path.read_text())) == 1
