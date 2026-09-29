"""摘要门停放清单只记录到达摘要阶段的失败。"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from dailyreport.__main__ import export_text
from dailyreport.collect import collect


NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
PUBLISHED = '2026-09-11T11:00:00+00:00'
GOOD_TEXT = ('研究团队今天发布人工智能模型，介绍了模型训练过程和测试方法。'
             '该模型支持中文文本处理，研究人员展示了多项测试中的运行结果。'
             '团队公布了模型的技术说明，其中列出了测试条件和数据使用范围。')


def failed_row(number, source='来源', abstract='  原文  内容\n第二行  '):
    return dict(title=f'Model {number} release', source_name=source,
                source_url=f'https://example.com/{number}', published=PUBLISHED,
                event_date=PUBLISHED, event_date_evidence='官方发布日期',
                content_kind='release', abstract=abstract)


def good_row():
    return dict(title='DeepSeek 新模型发布', source_name='正常来源',
                source_url='https://example.com/good', published=PUBLISHED)


class SummaryParkedTests(unittest.TestCase):
    def collect_rows(self, rows):
        def fetch(url):
            if url.endswith('/rss'):
                return '<rss><channel></channel></rss>'
            return '<article><p>' + GOOD_TEXT + '</p></article>'

        with (patch('dailyreport.collect._fetch', side_effect=fetch),
              patch('dailyreport.collect.select_recent', return_value=rows),
              patch('dailyreport.collect.article_event_evidence', return_value={
                  'event_date': '2026-09-11', 'event_date_evidence': '正文日期'}),
              patch('dailyreport.collect.english_summary', side_effect=ValueError('人工写稿'))):
            return collect({'sources': [{'name': '测试源', 'url': 'https://example.com/rss'}]},
                           NOW, 24, len(rows) + 1)

    def test_summary_failure_is_parked_and_stories_unchanged(self):
        result = self.collect_rows([failed_row(1), good_row()])
        self.assertEqual([story['title'] for story in result['stories']], ['DeepSeek 新模型发布'])
        self.assertEqual(result['collection_stats']['summary_rejected'], 1)
        self.assertEqual(result['collection_stats']['summary_parked'], 1)
        self.assertEqual(result['collection_stats']['summary_parked_overflow'], 0)
        self.assertEqual(result['summary_parked'], [dict(
            title='Model 1 release', source_name='来源', source_url='https://example.com/1',
            published=PUBLISHED, event_date=PUBLISHED,
            event_date_evidence='官方发布日期', reason='人工写稿', snippet='原文 内容 第二行')])
        with tempfile.TemporaryDirectory() as directory:
            export_text(result, Path(directory))
            self.assertIn('## 摘要门停放候选\n\n- 2026-09-11T11:00:00+00:00｜来源｜Model 1 release｜人工写稿｜https://example.com/1',
                          (Path(directory) / 'report.md').read_text(encoding='utf-8'))

    def test_source_limit_and_overflow(self):
        result = self.collect_rows([failed_row(i) for i in range(4)] + [good_row()])
        self.assertEqual(len(result['summary_parked']), 3)
        self.assertEqual(result['collection_stats']['summary_rejected'], 4)
        self.assertEqual(result['collection_stats']['summary_parked_overflow'], 1)

    def test_total_limit_and_newest_first(self):
        rows = [failed_row(i, source=f'来源{i // 3}') for i in range(33)]
        rows[0]['event_date'] = '2026-09-11T00:00:00+00:00'
        result = self.collect_rows(rows + [good_row()])
        self.assertEqual(len(result['summary_parked']), 30)
        self.assertEqual(result['collection_stats']['summary_parked_overflow'], 3)
        self.assertEqual(result['summary_parked'][0]['event_date'], PUBLISHED)
        self.assertNotIn('Model 0 release', [row['title'] for row in result['summary_parked']])

    def test_event_time_order_respects_timezones(self):
        older = failed_row(1, source='甲')
        newer = failed_row(2, source='乙')
        older['event_date'] = '2026-09-11T12:00:00+08:00'
        newer['event_date'] = '2026-09-11T05:00:00+00:00'
        result = self.collect_rows([older, newer, good_row()])
        self.assertEqual([row['title'] for row in result['summary_parked']],
                         ['Model 2 release', 'Model 1 release'])

    def test_same_fingerprint_only_parked_once(self):
        duplicate = failed_row(2)
        duplicate['title'] = 'Model 1 release!'
        result = self.collect_rows([failed_row(1), duplicate, good_row()])
        self.assertEqual(result['collection_stats']['summary_rejected'], 2)
        self.assertEqual(len(result['summary_parked']), 1)
        self.assertEqual(result['collection_stats']['summary_parked_overflow'], 0)

    def test_missing_original_is_empty_and_safe(self):
        result = self.collect_rows([failed_row(1, abstract=None), good_row()])
        self.assertEqual(result['summary_parked'][0]['snippet'], '')

    def test_date_rejected_and_off_topic_are_not_parked(self):
        feed = '''<rss><channel>
        <item><title>手机降价</title><link>https://example.com/off</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>
        <item><title>DeepSeek 新模型发布</title><link>https://example.com/old</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>
        <item><title>Qwen 新模型发布</title><link>https://example.com/good</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>
        </channel></rss>'''
        def fetch(url):
            return feed if url.endswith('/rss') else '<article><p>' + GOOD_TEXT + '</p></article>'
        def evidence(text, published, title, scope=None):
            date = '2026-09-01' if title.startswith('DeepSeek') else '2026-09-11'
            return {'event_date': date, 'event_date_evidence': '正文日期'}
        with (patch('dailyreport.collect._fetch', side_effect=fetch),
              patch('dailyreport.collect.article_event_evidence', side_effect=evidence)):
            result = collect({'sources': [{'name': '测试源', 'url': 'https://example.com/rss'}]},
                             NOW, 24, 3)
        self.assertEqual(result['collection_stats']['off_topic'], 1)
        self.assertEqual(result['collection_stats']['date_rejected'], 1)
        self.assertEqual(result['summary_parked'], [])
        self.assertEqual(result['collection_stats']['summary_parked'], 0)


if __name__ == '__main__':
    unittest.main()
