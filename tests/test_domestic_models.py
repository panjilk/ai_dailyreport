from datetime import datetime
from unittest.mock import patch

import pytest

from dailyreport.collect import _model_topic, _nav_label, collect
from dailyreport.international import english_topic
from dailyreport.models import model_labels
from dailyreport.recency import article_event_date, SHANGHAI


@pytest.mark.parametrize('title,label', [
    ('智谱上线新版本', 'GLM'), ('GLM-5升级编程能力', 'GLM'),
    ('月之暗面更新Kimi推理能力', 'Kimi'), ('深度求索推出新版本', 'DeepSeek'),
    ('千问上线新版本', 'Qwen'), ('豆包升级语音能力', '豆包'),
    ('文心一言更新推理能力', 'ERNIE'), ('腾讯混元开源新版本', 'Hunyuan'),
    ('MiniMax更新编程能力', 'MiniMax'), ('阶跃星辰发布新版本', '阶跃星辰'),
    ('书生开源新模型', 'InternLM'), ('百川推出新模型', '百川'),
    ('零一万物发布新模型', '零一万物'), ('讯飞星火升级理解能力', '星火'),
    ('Kimi新版本上线，后续接入办公软件', 'Kimi'),
        ('新创公司推出大模型', '大模型'),
])
def test_domestic_updates_and_navigation(title, label):
    assert _model_topic(title)
    assert _nav_label(title) == label


@pytest.mark.parametrize('title', ['智谱完成融资', '月之暗面任命高管', '手机接入Kimi，发布新版本', '豆包订阅套餐涨价'])
def test_unrelated_company_news_stays_out(title):
    assert not _model_topic(title)


def test_date_binding_recognizes_company_and_model_aliases():
    assert article_event_date('9月14日智谱上线新版本。', '2026-09-14', 'GLM新版本上线') == '2026-09-14'
    assert article_event_date('9月10日深度求索推出新版本。9月14日月之暗面升级推理能力。',
                              '2026-09-14', 'DeepSeek新版本发布') == '2026-09-10'


@pytest.mark.parametrize('brand', ['GLM', 'Zhipu', 'Kimi', 'Moonshot', 'Hunyuan', 'ERNIE', 'MiniMax', 'StepFun'])
def test_english_domestic_aliases(brand):
    assert english_topic(brand + ' release', 'New capabilities are available.')


@pytest.mark.parametrize('title', [
    'A step toward reliable databases',
    'Plant seed storage methods',
    'A spark of creativity in education',
    'Yi dynasty history',
])
def test_common_english_words_are_not_model_aliases(title):
    assert model_labels(title) == []
    assert not english_topic(title, 'Ordinary research without artificial intelligence.')


@patch('dailyreport.collect._fetch')
def test_domestic_update_flows_through_collection(fetch):
    fetch.side_effect = [
        '<rss><channel><item><title>月之暗面上线新版本</title><link>https://example.com/kimi</link>'
        '<pubDate>Mon, 14 Sep 2026 01:00:00 GMT</pubDate></item></channel></rss>',
        '<article><p>9月14日月之暗面上线新版本。Kimi支持中文文本处理，能够完成复杂推理任务。</p></article>',
    ]
    result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]},
                     datetime(2026, 9, 14, 12, tzinfo=SHANGHAI), 48, 1)
    assert result['stories'][0]['nav_label'] == 'Kimi'
    assert result['stories'][0]['event_date'] == '2026-09-14'
