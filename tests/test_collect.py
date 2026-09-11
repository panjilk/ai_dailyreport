import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dailyreport.collect import collect, select_recent, extract_paragraphs, _summary, classify, _bullet, _sentences


NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
TEXT = ('研究团队发布人工智能模型，介绍了模型训练过程和测试方法。'
        '该模型支持中文文本处理，研究人员展示了多项测试中的运行结果。'
        '团队公布了模型的技术说明，其中列出了测试条件和数据使用范围。'
        '文章同时介绍了系统的部署方式，并说明不同任务下的配置要求。'
        '开发者可以查阅公开的技术文档，了解接口参数与相关测试的详细记录。')


def item(title, published, url='https://example.com/a'):
    return dict(title=title, published=published, source_url=url)


class SelectionTests(unittest.TestCase):
    def test_dates_boundaries_and_offsets(self):
        rows = [item('boundary', '2026-09-10T20:00:00+08:00'),
                item('old', '2026-09-10T11:59:59Z', 'https://e.com/old'),
                item('future', '2026-09-11T12:00:01Z'), item('missing', None),
                item('naive', '2026-09-11T10:00:00'),
                item('GMT', 'Fri, 11 Sep 2026 11:00:00 GMT', 'https://e.com/new')]
        result = select_recent(rows, NOW, 24, 8)
        self.assertEqual([r['title'] for r in result], ['GMT', 'boundary'])
        self.assertEqual(datetime.fromisoformat(result[0]['published']).utcoffset().total_seconds(), 0)

    def test_tracking_and_title_dedup(self):
        rows = [item('模型 发布！', NOW.isoformat(), 'https://EXAMPLE.com/a?utm_source=x&id=2#top'),
                item('different', NOW.isoformat(), 'https://example.com/a?id=2&utm_medium=y'),
                item('模型发布', NOW.isoformat(), 'https://example.com/b')]
        self.assertEqual(len(select_recent(rows, NOW, 24, 8)), 1)
        self.assertEqual(select_recent(rows, NOW, 24, 8)[0]['source_url'], 'https://example.com/a?id=2')

    def test_invalid_arguments(self):
        for hours, limit in [(0, 2), (24, 0), (-1, 2)]:
            with self.assertRaises(ValueError):
                select_recent([], NOW, hours, limit)
        with self.assertRaises(ValueError):
            select_recent([], NOW.replace(tzinfo=None), 24, 8)


class ClassificationTests(unittest.TestCase):
    def test_categories_and_fallback(self):
        cases = [
            ('公司发布新一代大模型', '', '模型发布'),
            ('开发者 SDK 开放下载', '', '开发生态'),
            ('手机上线人工智能助手', '', '产品应用'),
            ('论文分析模型推理架构', '', '技术洞察'),
            ('人工智能公司完成融资', '', '行业动态'),
            ('今日新闻', '', '要闻'),
            ('最新消息', '团队发布新模型。', '模型发布'),
            ('公司完成融资', '资金用于发布新模型和 SDK。', '行业动态'),
            ('模型发布并开放 API', '', '模型发布'),
            ('Daily railway update', '', '要闻'),
        ]
        for title, narration, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify(title, narration), expected)
                self.assertEqual(classify(title, narration), classify(title, narration))


class CollectionTests(unittest.TestCase):
    @patch('dailyreport.collect._fetch')
    def test_fake_model_denial_is_skipped_with_reason(self, fetch):
        fake = ('网传消息如下。新模型已经全面超过所有现有人工智能系统，并将在本月面向全球所有用户免费开放。'
                '该模型已经获得多家科研机构共同认证，可以在没有任何人工监督的情况下完成全部科研任务。'
                '开发团队已经向所有企业开放完整模型权重，并承诺未来所有版本都不会收取任何服务费用。'
                '以上消息均为虚假信息。')
        feed = '<rss><channel>' + ''.join(f'<item><title>{title}</title><link>https://example.com/{path}</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>' for title, path in [('AI 新模型消息', 'fake'), ('人工智能模型发布', 'good')]) + '</channel></rss>'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + (fake if url.endswith('fake') else TEXT) + '</p></article>'
        result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, NOW, 24, 2)
        self.assertEqual([s['source_url'] for s in result['stories']], ['https://example.com/good'])
        self.assertEqual(len(result['collection_errors']), 1)
        self.assertIn('辟谣或纠正', result['collection_errors'][0])
        for title, body in [('AI 模型辟谣', TEXT), ('AI 模型消息', fake)]:
            with self.assertRaisesRegex(ValueError, '辟谣或纠正'):
                _summary([body], title)

    def test_narration_is_contiguous_and_keeps_attribution_lead(self):
        attribution = '研究团队表示：'
        claims = ('“新模型可能提升部分中文任务的处理速度，但结果仅适用于内部测试，尚未经过独立验证。”'
                  '研究团队还说明，不同任务需要使用不同的测试配置，因此这些结果不能直接推及其他场景。'
                  '团队公布了相关技术说明，其中列出了测试条件和数据使用范围，并提示使用者检查具体版本。')
        _, narration = _summary([attribution, claims], '新模型中文任务测试结果')
        self.assertTrue(narration.startswith(attribution))
        self.assertIn(narration, attribution + claims)
        self.assertIn('尚未经过独立验证', narration)

    def test_cannot_skip_long_attributed_lead_for_unqualified_claims(self):
        lead = '据未经证实的匿名来源称，' + '团队可能正在研究新的中文模型训练方法，' * 9 + '目前尚无独立证据。'
        with self.assertRaisesRegex(ValueError, '连续'):
            _summary([lead, TEXT], '中文模型训练方法')

    @patch('dailyreport.collect._fetch')
    def test_general_feed_rejects_tangential_hardware_ai_mentions(self, fetch):
        rows = [
            ('石头 G30S Ultra 体验：41000Pa、75℃ 活水与 8.98cm 机身，年度旗舰答卷', '新增 AI 自升降滚筒罩和 AI 智控清洁液。'),
            ('全新一代智己 LS6 将于 9 月 23 日上市，预售价 20.99 万元起', '车型提供多种电池配置，支持 AI 智能驾驶。'),
            ('乡村数字消费方案公布', '介绍家电消费政策。' * 20 + '支持人工智能与乡村教育融合。'),
            ('团队公布新研究成果', '研究人员公布大语言模型训练方法，并说明测试条件。'),
            ('AI 安全风险引发讨论', '研究人员介绍相关风险。'),
        ]
        entries = ''.join(f'<item><title>{title}</title><description>{desc}</description><link>https://example.com/{i}</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>' for i, (title, desc) in enumerate(rows))
        feed = '<rss><channel>' + entries + '</channel></rss>'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
        result = collect({'sources': [{'name': '综合新闻', 'url': 'https://example.com/rss'}]}, NOW, 24, 8)
        self.assertEqual([s['title'] for s in result['stories']], [row[0] for row in rows[3:]])
        self.assertEqual(fetch.call_count, 3)

    def test_safety_related_link_not_article_evidence(self):
        related = 'AI 智能体出现失控行为，OpenAI 呼吁美国出台强制性全国 AI 安全法规'
        factual = '陈嘉兴表示，应该警惕现实 AI 安全风险，相关案例仍需结合具体情况分析。'
        html = '<div id="paragraph"><p>' + factual + '</p><p>《 <a href="/related">' + related + '</a> 》</p><p><a href="/other">' + related + '</a></p><p>研究人员在<a href="/paper">技术报告</a>中说明了人工智能系统的测试条件和使用范围。</p></div>'
        paragraphs = extract_paragraphs(html)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0], factual)
        self.assertNotIn(related, ''.join(paragraphs))
        self.assertIn('技术报告', paragraphs[1])

    def test_summary_keeps_qualified_lead_not_questions_or_filler(self):
        lead = '据知情人士透露，Kimi K3 模型可能提升部分中文任务的处理速度，但结果仅适用于内部测试，尚未经过独立验证。'
        detail = '团队公布了相关技术说明，其中列出了模型测试使用的数据范围，并指出不同任务的结果不能直接进行比较。'
        extra = '研究人员表示，后续将继续检查系统运行记录，并公开更多测试细节。'
        filler = ['那么，Kimi K3 模型究竟升级了什么？', '放到真实家庭环境里，又能带来怎样的体验？', 'Kimi K3 模型的表现要干脆不少。', 'Kimi K3 模型交出了一份年度旗舰答卷。']
        bullets, narration = _summary([*filler, lead, detail, extra], 'Kimi K3 模型测试结果公布')
        self.assertTrue(narration.startswith(lead))
        self.assertIn(detail, narration)
        self.assertTrue(120 <= len(narration) <= 160)
        for sentence in filler:
            self.assertNotIn(sentence, narration)
        self.assertEqual(bullets[0], lead)

    def test_bullet_preserves_complete_sentence_and_qualifiers(self):
        sentence = '据知情人士透露，团队预计新模型可能提升部分中文任务的处理速度，但该结果仅适用于内部测试，尚未经过独立验证。'
        self.assertEqual(_bullet(sentence), sentence)

    def test_long_bullet_marks_omission_at_clause_boundary(self):
        prefix = '据团队介绍，该模型目前仅在内部测试中支持中文文本分析，'
        sentence = prefix + '研究人员仍在检查不同任务的运行结果与详细数据记录' * 4 + '。'
        self.assertEqual(_bullet(sentence), prefix + '…')
        unbroken = '据团队介绍' + '模型仍处于内部测试阶段' * 8 + '。'
        bullet = _bullet(unbroken)
        self.assertLessEqual(len(bullet), 70)
        self.assertTrue(bullet.endswith('…'))
        self.assertTrue(unbroken.startswith(bullet[:-1]))

    def test_quoted_sentence_keeps_attribution_and_closing_quote(self):
        quote = '研究人员表示：“模型可能提升处理速度。结果仅适用于内部测试。”'
        self.assertEqual(_sentences(quote + '团队尚未公布独立测试数据。'), [quote, '团队尚未公布独立测试数据。'])
        self.assertEqual(_bullet(quote), quote)

    def test_bullets_are_informative_source_spans(self):
        text = '此外，研究团队公布人工智能模型的测试结果，并详细说明了实验使用的数据范围。部分知情人士透露，团队计划继续开展中文文本任务测试，并公布相应技术文档。该模型支持中文文本处理，研究人员展示了多项测试中的运行结果。团队公布了模型的技术说明，其中列出了测试条件和数据使用范围。'
        bullets, narration = _summary([text], '人工智能模型测试')
        self.assertTrue(all(16 <= len(b) <= 70 and b in text for b in bullets))
        self.assertTrue(120 <= len(narration) <= 160)

    def test_shanghai_date_rollover(self):
        with patch('dailyreport.collect._fetch') as fetch:
            fetch.side_effect = ['<rss><channel><item><title>AI模型</title><link>https://example.com/a</link><pubDate>Fri, 11 Sep 2026 16:00:00 GMT</pubDate></item></channel></rss>', '<article><p>' + TEXT + '</p></article>']
            result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, datetime(2026, 9, 11, 17, tzinfo=timezone.utc), 24, 1)
            self.assertEqual(result['date'], '2026-09-12')

    def test_article_content_excludes_navigation_ads(self):
        html = '<nav><p>导航人工智能新闻</p></nav><div id="paragraph"><p>' + TEXT + '</p><div class="advert"><p>广告内容购买产品</p></div></div><footer>版权</footer>'
        self.assertEqual(extract_paragraphs(html), [TEXT])
        self.assertEqual(extract_paragraphs('<body><nav>' + TEXT + '</nav><p>' + TEXT + '</p></body>'), [])

    @patch('dailyreport.collect._fetch')
    def test_article_failures_are_nonfatal_and_requests_bounded(self, fetch):
        entries = ''.join(f'<item><title>人工智能模型{i}</title><link>https://example.com/{i}</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>' for i in range(50))
        feed = '<rss><channel>' + entries + '</channel></rss>'
        def response(url):
            if url.endswith('rss'):
                return feed
            if url.endswith('/0'):
                raise OSError('article timeout')
            return '<article><p>' + TEXT + '</p></article>'
        fetch.side_effect = response
        result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, NOW, 24, 100)
        self.assertEqual(len(result['stories']), 19)
        self.assertEqual(len(result['collection_errors']), 1)
        self.assertEqual(fetch.call_count, 21)

    @patch('dailyreport.collect._fetch')
    def test_collection_schema_and_nonfatal_source_error(self, fetch):
        feed = '<rss version="2.0"><channel><title>新闻</title><item><title>人工智能模型发布</title><link>https://example.com/a</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item></channel></rss>'
        def response(url):
            if url.endswith('bad'):
                raise OSError('unavailable')
            return feed if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
        fetch.side_effect = response
        config = {'sources': [{'name': '坏源', 'url': 'https://example.com/bad', 'enabled': True, 'ai_only': False}, {'name': '新闻', 'url': 'https://example.com/rss', 'enabled': True, 'ai_only': False}]}
        result = collect(config, NOW, 24, 8)
        self.assertEqual(set(result), {'date', 'window_days', 'window_hours', 'title', 'edition_note', 'stories', 'collection_errors'})
        self.assertEqual(result['date'], '2026-09-11')
        story = result['stories'][0]
        self.assertEqual(set(story), {'id', 'category', 'title', 'bullets', 'narration', 'source_name', 'source_url', 'published', 'evidence', 'verification'})
        self.assertEqual(story['verification'], 'extractive')
        self.assertEqual(story['category'], '模型发布')
        self.assertTrue(120 <= len(story['narration']) <= 160)
        self.assertTrue(2 <= len(story['bullets']) <= 3)
        self.assertIn('机器抽取', result['edition_note'])
        self.assertEqual(len(result['collection_errors']), 1)
        for bullet in story['bullets']:
            self.assertIn(bullet, TEXT)

    @patch('dailyreport.collect._fetch', return_value='<html>not RSS</html>')
    def test_empty_is_clear_failure(self, fetch):
        with self.assertRaisesRegex(RuntimeError, '没有.*资讯'):
            collect({'sources': [{'name': 'bad', 'url': 'https://example.com', 'enabled': True}]}, NOW, 24, 2)

    @patch('dailyreport.collect._fetch')
    def test_ai_filter_word_boundaries_and_specific_source(self, fetch):
        feed = '<rss><channel><item><title>Daily railway update</title><link>https://example.com/a</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item></channel></rss>'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
        source = dict(name='test', url='https://example.com/rss', enabled=True, ai_only=False)
        with self.assertRaises(RuntimeError):
            collect({'sources': [source]}, NOW, 24, 1)
        source['ai_only'] = True
        self.assertEqual(len(collect({'sources': [source]}, NOW, 24, 1)['stories']), 1)


if __name__ == '__main__':
    unittest.main()
