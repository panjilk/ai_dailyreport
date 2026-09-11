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
