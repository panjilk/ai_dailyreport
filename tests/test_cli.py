import json
import subprocess
import sys

from dailyreport.__main__ import export_text, write_preview


def fixture():
    return {'date': '2026-09-11', 'window_days': 1, 'edition_note': '来源已保存', 'stories': [
        {'title': '<script>alert(1)</script>', 'category': '要闻', 'bullets': ['第一点'],
         'narration': '这是一条测试资讯。', 'source_name': 'Example',
         'source_url': 'https://example.com/news?a=1&b=2', 'published': '2026-09-11'}]}


def test_export_preserves_sources_and_narration(tmp_path):
    export_text(fixture(), tmp_path)
    assert json.loads((tmp_path / 'briefing.json').read_text('utf-8'))['stories'][0]['source_url'] == 'https://example.com/news?a=1&b=2'
    assert 'https://example.com/news?a=1&b=2' in (tmp_path / 'report.md').read_text('utf-8')
    assert '这是一条测试资讯。' in (tmp_path / 'script.txt').read_text('utf-8')


def test_preview_escapes_untrusted_article_titles(tmp_path):
    write_preview(fixture(), tmp_path)
    page = (tmp_path / 'index.html').read_text('utf-8')
    assert '<script>alert(1)</script>' not in page
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page
    assert '<video' not in page


def test_invalid_limit_fails_before_collection():
    p = subprocess.run([sys.executable, '-m', 'dailyreport', '--limit', '0'], capture_output=True)
    assert p.returncode == 2


def test_invalid_pitch_fails_before_collection():
    p = subprocess.run([sys.executable, '-m', 'dailyreport', '--pitch', '-21'], capture_output=True)
    assert p.returncode == 2


def test_import_keeps_old_edition_label_but_filters_against_search_time(tmp_path, monkeypatch):
    from copy import deepcopy
    from datetime import datetime
    import dailyreport.__main__ as cli
    from dailyreport.recency import SHANGHAI

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 13, 12, tzinfo=SHANGHAI)

    monkeypatch.setattr(cli, 'datetime', Clock)
    briefing = fixture()
    briefing['search_date'] = '2026-09-11'
    current = deepcopy(briefing['stories'][0])
    current.update(title='当前模型', published='2026-09-12', event_date='2026-09-12')
    briefing['stories'][0].update(published='2026-09-08', event_date='2026-09-08')
    briefing['stories'].append(current)
    source = tmp_path / 'input.json'
    source.write_text(json.dumps(briefing), encoding='utf-8')
    output = tmp_path / 'result'
    assert cli.main(['--input', str(source), '--output', str(output), '--collect-only']) == 0
    result = json.loads((output / 'briefing.json').read_text('utf-8'))
    assert result['date'] == '2026-09-11'
    assert result['search_date'] == '2026-09-13'
    assert [s['title'] for s in result['stories']] == ['当前模型']
    assert len(result['excluded_stories']) == 1
    assert '2026年09月09日 00:00 — 09月13日 12:00' in (output / 'index.html').read_text('utf-8')
    assert '导入稿件筛选' in (output / 'report.md').read_text('utf-8')
    assert not (output / 'daily.mp4').exists()

    briefing['stories'] = briefing['stories'][:1]
    source.write_text(json.dumps(briefing), encoding='utf-8')
    rejected_output = tmp_path / 'rejected'
    assert cli.main(['--input', str(source), '--output', str(rejected_output), '--collect-only']) == 1
    assert not rejected_output.exists()


def test_import_honors_24_hour_window_and_reports_actual_bounds(tmp_path, monkeypatch):
    from datetime import datetime
    import dailyreport.__main__ as cli
    from dailyreport.recency import SHANGHAI

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 13, 12, tzinfo=SHANGHAI)

    monkeypatch.setattr(cli, 'datetime', Clock)
    briefing = fixture()
    briefing['stories'][0].update(
        title='当前事件', published='2026-09-13T08:00:00+08:00', event_date='2026-09-13')
    old_event = dict(briefing['stories'][0])
    old_event.update(title='更早事件', published='2026-09-13T09:00:00+08:00', event_date='2026-09-11')
    briefing['stories'].append(old_event)
    source = tmp_path / 'input-24h.json'
    source.write_text(json.dumps(briefing), encoding='utf-8')
    output = tmp_path / 'result-24h'

    assert cli.main([
        '--input', str(source), '--hours', '24', '--output', str(output), '--collect-only']) == 0

    result = json.loads((output / 'briefing.json').read_text('utf-8'))
    assert [s['title'] for s in result['stories']] == ['当前事件']
    assert result['window_hours'] == 24
    assert result['window_start'] == '2026-09-12T12:00:00+08:00'
    assert result['window_end'] == '2026-09-13T12:00:00+08:00'
    assert '2026年09月12日 12:00 — 09月13日 12:00' in (output / 'report.md').read_text('utf-8')
