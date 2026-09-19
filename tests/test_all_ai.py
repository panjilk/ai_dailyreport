from datetime import datetime
from unittest.mock import patch
import pytest

from dailyreport.collect import collect, classify
from dailyreport.recency import SHANGHAI, article_event_evidence, enforce_recency
from dailyreport.topics import ai_related, news_priority


@pytest.mark.parametrize('title,text,category', [
    ('GPT用量重置', '9月14日OpenAI宣布重置ChatGPT用户的用量。', '产品应用'),
    ('AI监管法案通过', '9月14日议会通过人工智能监管法案。', '行业动态'),
    ('AI影响选举讨论', '9月14日议会讨论AI对选举的影响。', '行业动态'),
    ('AI公司完成融资', '9月14日人工智能公司完成融资。', '行业动态'),
])
def test_non_model_events_have_date_evidence(title, text, category):
    assert ai_related(title)
    assert article_event_evidence(text, '2026-09-14', title, scope='all_ai')['event_date'] == '2026-09-14'
    assert classify(title, text) == category


def test_general_event_still_rejects_future_plans_and_old_reposts():
    with pytest.raises(ValueError):
        article_event_evidence('9月14日计划重置GPT用量。', '2026-09-14', 'GPT用量重置', scope='all_ai')
    assert article_event_evidence('9月14日消息，回顾8月20日议会通过AI法案。', '2026-09-14', 'AI法案', scope='all_ai')['event_date'] == '2026-08-20'
    assert not ai_related('议会讨论普通交通法案')


@patch('dailyreport.collect._fetch')
def test_priority_applies_before_limit_and_survives_final_sort(fetch):
    titles = ['AI监管法案通过', 'ChatGPT用量重置', 'GLM新版本发布']
    dates = ['2026-09-14T11:00:00+08:00', '2026-09-14T10:00:00+08:00', '2026-09-13T10:00:00+08:00']
    texts = ['9月14日议会通过AI监管法案。该法案规定了人工智能系统的评估要求。',
             '9月14日OpenAI宣布重置ChatGPT用量。用户可以重新使用服务。',
             '9月13日智谱发布GLM新版本。该版本提升中文推理能力。']
    feed = '<rss><channel>' + ''.join(f'<item><title>{title}</title><link>https://example.com/{i}</link><pubDate>{dates[i]}</pubDate></item>' for i, title in enumerate(titles)) + '</channel></rss>'
    fetch.side_effect = lambda url: feed if url.endswith('/rss') else '<article><p>' + texts[int(url.rsplit('/', 1)[1])] + '</p></article>'
    now = datetime(2026, 9, 14, 12, tzinfo=SHANGHAI)
    result = collect({'topic_scope': 'all_ai', 'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, now, 48, 2)
    enforce_recency(result, now)
    assert [s['title'] for s in result['stories']] == [titles[2], titles[1]]
    assert [news_priority(s) for s in result['stories']] == [0, 1]
    assert fetch.call_count == 3
