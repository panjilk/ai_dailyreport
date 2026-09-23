from datetime import datetime
from unittest.mock import patch
import pytest

from dailyreport.collect import collect, classify
from dailyreport.recency import SHANGHAI, article_event_evidence, enforce_recency
from dailyreport.topics import ai_related, editorial_candidate, news_priority, playback_priority


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


@pytest.mark.parametrize('title', [
    'AI 早报：三家公司发布新品',
    'ChatGPT 更新；苹果发布手机；车企公布销量',
    '千万奖金只等最会用 AI 的你',
])
def test_roundups_and_promotions_are_not_ranked_as_news(title):
    assert not editorial_candidate(title)


def test_same_heat_level_keeps_newest_story_first():
    stories = [
        {'title': 'ChatGPT 接入办公软件', 'published': '2026-09-18'},
        {'title': 'Claude 接入开发工具', 'published': '2026-09-19'},
    ]
    assert news_priority(stories[0]) == news_priority(stories[1]) == 1


def test_model_news_plays_before_newer_general_ai_news():
    from dailyreport.recency import enforce_recency
    stories = [
        {'title': 'AI眼镜出货量增长', 'published': '2026-09-22T10:00:00+08:00', 'event_date': '2026-09-22'},
        {'title': 'OpenAI升级GPT推理能力', 'published': '2026-09-21T10:00:00+08:00', 'event_date': '2026-09-21'},
        {'title': '智谱发布GLM新版本', 'published': '2026-09-20T10:00:00+08:00', 'event_date': '2026-09-20'},
    ]
    briefing = {'date': '2026-09-22', 'stories': stories}
    enforce_recency(briefing, datetime(2026, 9, 22, 12, tzinfo=SHANGHAI))
    assert [story['title'] for story in briefing['stories']] == [stories[2]['title'], stories[1]['title'], stories[0]['title']]


def test_comparison_target_does_not_count_as_model_news():
    assert playback_priority({'title': 'Meta Muse下载量超过ChatGPT同期'})[0] == 1
    assert playback_priority({'title': 'Claude推出新版本'})[0] == 0
    assert playback_priority({'title': 'DeepSeek升级推理能力'})[0] == 0
    assert playback_priority({'title': 'OpenAI与独立咨询小组合作审查AI成果'})[0] == 0
    assert playback_priority({'title': '阿里开源 Qwen-Image-2.1', 'category': '模型发布'}) < playback_priority({'title': '智谱 ZCode 更新 GLM 编程工作流', 'category': '开发生态'})


@pytest.mark.parametrize('title', [
    'DeepSeek 新模型正式发布',
    'GPT-6 推理能力升级',
    'GLM 新版本发布',
    'Claude 5 正式上线',
    'Anthropic 发布 Claude Opus 5.5',
    'SpaceXAI 发布 Grok Voice Transcribe 2.0 语音转文本模型：错误率降低约一半，价格保持不变',
    'Grok Voice Transcribe 2.0 speech-to-text model launches today',
])
def test_only_explicit_model_milestones_enter_hottest_tier(title):
    assert news_priority({'title': title}) == 0


@pytest.mark.parametrize('title', [
    'OpenAI 发布年度安全报告',
    'Anthropic 发布 Claude 安全报告',
    'ChatGPT 上线群聊功能',
    'Claude 推出桌面端功能',
    'ChatGPT Voice 2.0 上线群聊功能',
    'ChatGPT Voice 2.0 客户端接入语音模型',
    'Grok Voice Transcribe 2.0 模型发布评测报告',
])
def test_company_reports_and_product_features_do_not_enter_hottest_tier(title):
    assert news_priority({'title': title}) == 1


@pytest.mark.parametrize('title', [
    'OpenAI 示警：先进 AI 可在 2 台相邻物理隔离 PC 间“对话”',
    '研究人员警告 AI 智能体存在数据泄露隐患',
    'OpenAI warns that AI agents can expose private data',
])
def test_ai_warnings_enter_hot_tier(title):
    assert news_priority({'title': title}) == 1
