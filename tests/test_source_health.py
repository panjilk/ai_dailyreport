from dailyreport.source_health import load_health, record_result, save_health


def test_failure_count_and_threshold(tmp_path):
    path = tmp_path / 'health.json'
    health = {}
    for count in range(1, 4):
        assert record_result(health, '源', 'timeout', '2026-09-29T00:00:00Z') == (count >= 3)
        assert health['源']['consecutive_failures'] == count
        save_health(path, health)
        health, warnings = load_health(path)
        assert not warnings
    assert health['源']['last_error'] == 'timeout'


def test_success_resets_count():
    health = {'源': {'consecutive_failures': 7}}
    assert not record_result(health, '源')
    assert health['源']['consecutive_failures'] == 0
    assert health['源']['last_error'] == ''


def test_broken_file_degrades(tmp_path):
    path = tmp_path / 'health.json'
    path.write_text('{broken')
    health, warnings = load_health(path)
    assert health == {}
    assert warnings


def test_collect_prints_stale_warning_and_persists(tmp_path, monkeypatch, capsys):
    from datetime import datetime, timezone
    from dailyreport.collect import collect

    feed = ('<rss><channel><item><title>DeepSeek 模型发布</title>'
            '<link>https://example.test/story</link>'
            '<pubDate>Tue, 29 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>')
    def response(url):
        if url.endswith('/bad'):
            raise OSError('read timeout')
        if url.endswith('/rss'):
            return feed
        return '<article><p>9月29日研究团队发布DeepSeek新模型。模型支持中文文本处理，能够完成复杂推理任务。</p></article>'

    monkeypatch.setattr('dailyreport.collect._fetch', response)
    path = tmp_path / 'health.json'
    config = {'sources': [{'name': '超时源', 'url': 'https://example.test/bad'},
                          {'name': '正常源', 'url': 'https://example.test/rss'}]}
    now = datetime(2026, 9, 29, 1, tzinfo=timezone.utc)
    for _ in range(3):
        result = collect(config, now, 24, 1, health_path=path)
    assert '[源疑似失效] 超时源：连续失败 3 次' in capsys.readouterr().out
    assert result['stale_sources'][0]['name'] == '超时源'
    health, _ = load_health(path)
    assert health['超时源']['consecutive_failures'] == 3
    assert health['正常源']['consecutive_failures'] == 0
