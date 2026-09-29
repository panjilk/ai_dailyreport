"""采集并发的顺序、上限和缓存回归测试。"""

import json
import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from dailyreport.concurrency import collection_workers, run_ordered
from dailyreport import international as tr
from dailyreport.collect import collect
from dailyreport.broadcast_log import url_fingerprint


def test_ordered_results():
    def work(item):
        time.sleep((4 - item) * 0.005)
        return item * 2
    assert run_ordered([1, 2, 3], work, 3) == [2, 4, 6]


def test_worker_limit():
    lock = threading.Lock()
    active = peak = 0
    def work(item):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.005)
        with lock:
            active -= 1
        return item
    assert run_ordered(range(20), work, 3) == list(range(20))
    assert 1 < peak <= 3


def test_single_worker_is_serial():
    seen = []
    assert run_ordered(range(4), lambda item: (seen.append(item), item)[1], 1) == list(range(4))
    assert seen == list(range(4))


def test_exception_stays_at_its_index():
    def work(item):
        if item == 2:
            raise ValueError('失败')
        return item
    result = run_ordered([1, 2, 3], work, 3)
    assert result[0] == 1 and isinstance(result[1], ValueError) and result[2] == 3


def test_config_and_environment(monkeypatch):
    assert collection_workers({}) == 6
    monkeypatch.setenv('COLLECT_CONCURRENCY', '1')
    assert collection_workers({'collection_concurrency': 99}) == 1
    for value in ('0', '17', '1.5', '-1'):
        monkeypatch.setenv('COLLECT_CONCURRENCY', value)
        with pytest.raises(ValueError):
            collection_workers({})
    monkeypatch.delenv('COLLECT_CONCURRENCY')
    with pytest.raises(ValueError):
        collection_workers({'collection_concurrency': True})


def test_concurrent_cache_writes_keep_all_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, 'CACHE_PATH', tmp_path / 'translation_cache.json')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': '中文译文。'}}]}
    def work(item):
        return tr.translate_to_chinese(f'Unique English sentence {item}.',
                                       lambda *_a, **_k: Response())
    assert run_ordered(range(30), work, 6) == ['中文译文。'] * 30
    assert len(json.loads(tr.CACHE_PATH.read_text(encoding='utf-8'))) == 30


def test_same_input_collects_same_stories_and_parked(monkeypatch):
    published = '2026-09-11T11:00:00+00:00'
    good_text = ('研究团队今天发布人工智能模型，介绍了模型训练过程和测试方法。'
                 '该模型支持中文文本处理，研究人员展示了多项测试中的运行结果。'
                 '团队公布了模型的技术说明，其中列出了测试条件和数据使用范围。')
    rows = [dict(title='Model 1 release', source_name='来源',
                 source_url='https://example.com/failed', published=published,
                 event_date=published, event_date_evidence='官方发布日期',
                 content_kind='release', abstract='原文内容'),
            dict(title='DeepSeek 新模型发布', source_name='正常来源',
                 source_url='https://example.com/good', published=published),
            dict(title='Model X Release', source_name='英文来源',
                 source_url='https://example.com/release', published=published,
                 event_date=published, event_date_evidence='官方发布日期',
                 content_kind='official_model_release', abstract='Model X is released.',
                 feature_points=['Model X supports reasoning.'])]
    def fetch(url):
        if url.endswith('/rss'):
            return '<rss><channel></channel></rss>'
        return '<article><p>' + good_text + '</p></article>'
    config = {'sources': [{'name': '一', 'url': 'https://example.com/1/rss'},
                          {'name': '二', 'url': 'https://example.com/2/rss'}]}
    outputs = []
    with (patch('dailyreport.collect._fetch', side_effect=fetch),
          patch('dailyreport.collect.select_recent', return_value=rows),
          patch('dailyreport.collect.article_event_evidence', return_value={
              'event_date': '2026-09-11', 'event_date_evidence': '正文日期'}),
          patch('dailyreport.collect.english_summary', side_effect=ValueError('人工写稿')),
          patch('dailyreport.collect.translate_to_chinese', return_value='模型X发布。')):
        for workers in ('1', '6'):
            monkeypatch.setenv('COLLECT_CONCURRENCY', workers)
            outputs.append(collect(config, datetime(2026, 9, 11, 12, tzinfo=timezone.utc), 24, 3))
    for output in outputs:
        assert len(output['stories']) == 2 and len(output['summary_parked']) == 1
    def identity(output):
        return [(story['title'], url_fingerprint(story['source_url'], story['title']))
                for story in output['stories']]
    assert identity(outputs[0]) == identity(outputs[1])
    assert outputs[0]['summary_parked'] == outputs[1]['summary_parked']
    assert outputs[0]['collection_errors'] == outputs[1]['collection_errors']
    assert {k: v for k, v in outputs[0]['collection_stats'].items() if k != 'timings'} == {
        k: v for k, v in outputs[1]['collection_stats'].items() if k != 'timings'}
