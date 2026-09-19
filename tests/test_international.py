import json
from datetime import datetime
from unittest.mock import patch

import pytest

from dailyreport.collect import collect
from dailyreport.international import source_rows, paper_details, english_summary, english_topic
from dailyreport.recency import SHANGHAI

NOW = datetime(2026, 9, 14, 20, tzinfo=SHANGHAI)
ABSTRACT = 'We introduce a language model for reasoning. Results improve accuracy on a public benchmark. However, evaluation is limited to English tasks.'


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


def test_release_date_and_stable_only():
    entry = dict(tag_name='v5.0', html_url='https://github.com/a/b/releases/tag/v5.0',
                 published_at='2026-09-13T10:00:00Z', updated_at='2026-09-14T10:00:00Z', body=ABSTRACT)
    rows = list(source_rows({'type': 'github_releases', 'name': 'Transformers'}, json.dumps([
        entry, dict(entry, draft=True), dict(entry, prerelease=True)])))
    assert len(rows) == 1
    assert rows[0]['event_date'] == entry['published_at']


@patch('dailyreport.collect._fetch')
def test_english_paper_reaches_briefing_without_chinese_regex(fetch):
    feed = json.dumps([{'paper': {'id': '2609.12345', 'title': 'LLM Reasoning',
                       'publishedAt': '2026-09-13T10:00:00Z', 'summary': ABSTRACT}}])
    fetch.side_effect = [feed, paper_page()]
    result = collect({'sources': [{'name': 'HF', 'url': 'https://huggingface.co/api/daily_papers', 'type': 'hf_papers'}]}, NOW, 48, 1)
    story = result['stories'][0]
    assert story['language'] == 'en'
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


@patch('dailyreport.collect._fetch')
def test_release_reaches_briefing_without_article_fetch(fetch):
    fetch.return_value = json.dumps([dict(tag_name='v5.0', html_url='https://github.com/a/b/releases/tag/v5.0',
                                       published_at='2026-09-13T10:00:00Z', body=ABSTRACT)])
    result = collect({'sources': [{'name': 'Transformers', 'url': 'https://api.github.com/repos/a/b/releases', 'type': 'github_releases'}]}, NOW, 48, 1)
    assert result['stories'][0]['category'] == '开发生态'
    assert fetch.call_count == 1
    assert result['collection_stats']['article_requests'] == 0


def test_arxiv_replacements_are_not_new_papers():
    xml = '''<rss xmlns:arxiv="http://arxiv.org/schemas/atom"><channel>
    <item><title>LLM paper</title><link>https://arxiv.org/abs/2609.12345</link>
    <description>Abstract: language model evaluation.</description><arxiv:announce_type>replace</arxiv:announce_type></item>
    </channel></rss>'''
    assert list(source_rows({'type': 'arxiv'}, xml)) == []
