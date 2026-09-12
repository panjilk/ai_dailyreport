import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dailyreport.collect import collect, select_recent, extract_paragraphs, _summary, classify, _bullet, _sentences, _model_topic, _nav_label


NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
TEXT = ('研究团队今天发布人工智能模型，介绍了模型训练过程和测试方法。'
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
        result = collect({'topic_scope': 'all_ai', 'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, NOW, 24, 2)
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
        self.assertTrue(narration.startswith('新模型中文任务测试结果。' + attribution))
        self.assertIn('不同任务需要使用不同的测试配置', narration)
        self.assertIn(narration.removeprefix('新模型中文任务测试结果。'), attribution + claims)
        self.assertIn('尚未经过独立验证', narration)

    def test_cannot_skip_long_attributed_lead_for_unqualified_claims(self):
        lead = '据未经证实的匿名来源称，' + '团队可能正在研究新的中文模型训练方法，' * 9 + '目前尚无独立证据。'
        bullets, narration = _summary([lead, TEXT], '中文模型训练方法')
        self.assertIn(lead, narration)
        self.assertEqual(narration, '中文模型训练方法。' + ''.join(bullets))

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
        result = collect({'topic_scope': 'all_ai', 'sources': [{'name': '综合新闻', 'url': 'https://example.com/rss'}]}, NOW, 24, 8)
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
        self.assertTrue(narration.startswith('Kimi K3 模型测试结果公布。' + lead))
        self.assertIn(detail, narration)
        self.assertTrue(narration.endswith(''.join(bullets)))
        self.assertNotIn('…', narration)
        for sentence in filler:
            self.assertNotIn(sentence, narration)
        self.assertEqual(bullets[0], lead)

    def test_bullet_preserves_complete_sentence_and_qualifiers(self):
        sentence = '据知情人士透露，团队预计新模型可能提升部分中文任务的处理速度，但该结果仅适用于内部测试，尚未经过独立验证。'
        self.assertEqual(_bullet(sentence), sentence)

    def test_long_bullet_is_never_truncated(self):
        for sentence in [
            '据团队介绍，该模型目前仅在内部测试中支持中文文本分析，' +
            '研究人员仍在检查不同任务的运行结果与详细数据记录' * 4 + '。',
            '据团队介绍' + '模型仍处于内部测试阶段' * 8 + '。',
        ]:
            self.assertEqual(_bullet(sentence), sentence)

    def test_quoted_sentence_keeps_attribution_and_closing_quote(self):
        quote = '研究人员表示：“模型可能提升处理速度。结果仅适用于内部测试。”'
        self.assertEqual(_sentences(quote + '团队尚未公布独立测试数据。'), [quote, '团队尚未公布独立测试数据。'])
        self.assertEqual(_bullet(quote), quote)

    def test_bullets_are_informative_source_spans(self):
        text = '此外，研究团队公布人工智能模型的测试结果，并详细说明了实验使用的数据范围。部分知情人士透露，团队计划继续开展中文文本任务测试，并公布相应技术文档。该模型支持中文文本处理，研究人员展示了多项测试中的运行结果。团队公布了模型的技术说明，其中列出了测试条件和数据使用范围。'
        bullets, narration = _summary([text], '人工智能模型测试')
        self.assertTrue(all(len(b) >= 8 and b in text for b in bullets))
        self.assertTrue(narration.endswith(''.join(bullets)))
        self.assertNotIn('…', narration)

    def test_full_article_tail_details_survive_old_paragraph_and_sentence_limits(self):
        intro = '团队发布 Sites 人工智能建站工具，用户可以通过文本描述生成网站。'
        middle = [f'第{i}项演示展示了网站页面的布局效果和配色方案。' for i in range(205)]
        tail = 'Sites 支持绑定自定义域名，用户可以在设置中配置域名解析。'
        paragraphs = [intro, *middle, tail]
        cleaned = extract_paragraphs('<article>' + ''.join('<p>' + p + '</p>' for p in paragraphs) + '</article>')
        self.assertEqual(cleaned, paragraphs)
        bullets, narration = _summary(cleaned, 'Sites 人工智能建站工具发布！?!')
        self.assertIn(tail, narration)
        self.assertEqual(narration, 'Sites 人工智能建站工具发布。' + ''.join(bullets))
        self.assertTrue(1 <= len(bullets) <= 3)
        self.assertTrue(all(b in ''.join(paragraphs) for b in bullets))

    def test_late_limitation_and_its_attribution_are_retained(self):
        lead = '团队发布新模型，并公布中文文本处理接口和部署文档。'
        bridge = '文章列出了不同配置的演示记录以及开发环境的安装步骤。'
        attribution = '据匿名消息人士透露，这些性能结果可能来自内部测试。'
        claim = '模型在演示任务中提高了处理速度，并降低了运行资源消耗。'
        limit = '但上述结果尚未经过独立验证，模型不支持离线运行。'
        source = lead + bridge * 8 + attribution + claim + limit
        bullets, narration = _summary([source], '新模型发布')
        self.assertIn(attribution, narration)
        self.assertIn(claim, narration)
        self.assertIn(limit, narration)
        self.assertNotIn(bridge * 2, narration)
        self.assertEqual(narration, '新模型发布。' + ''.join(bullets))
        self.assertLessEqual(len(narration), 400)
        self.assertNotIn('…', narration)

    def test_all_five_keypoints_are_displayed_and_spoken(self):
        bullets, narration = _summary([TEXT], '人工智能模型发布。！？')
        self.assertLessEqual(len(bullets), 3)
        self.assertTrue(all(b in TEXT for b in bullets))
        self.assertEqual(narration, '人工智能模型发布。' + ''.join(bullets))
        self.assertNotIn('…', narration)

    def test_poor_or_incomplete_context_fails_explicitly(self):
        for text in ['', '模型发布了…',
                     '“模型是否能改变世界？”', TEXT[:-1] + '，但限制尚未说明…']:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, '正文不足|无法安全'):
                _summary([text], '模型发布')

    def test_long_data_background_is_not_reporting_context(self):
        lead = '据开发团队介绍，Sites 已上线人工智能建站功能，用户可以用自然语言描述页面需求，生成可编辑的网站并直接发布。'
        feature = 'Sites 支持继续修改页面布局和文字内容，用户可以在预览中检查实际效果，然后选择是否发布本次修改。'
        background = [f'历史资料第{i}页记录了早期数据中心的设备采购数据和仓库统计数据，当时的统计口径仅适用于旧版报表。' for i in range(70)]
        tail = 'Sites 支持绑定自定义域名，用户需要在域名服务商处配置解析记录，完成验证后即可通过自己的域名访问网站。'
        caveat = '但该域名功能目前仅向付费用户开放，尚未支持所有地区的域名服务商，具体可用范围需要在设置页面确认。'
        paragraphs = [lead, feature, *background, tail, caveat]
        bullets, narration = _summary(paragraphs, 'Sites 上线人工智能建站功能')
        for point in (lead, feature, tail, caveat):
            self.assertIn(point, narration)
        self.assertNotIn('历史资料', narration)
        self.assertTrue(180 <= len(narration) <= 400)
        self.assertEqual(narration, 'Sites 上线人工智能建站功能。' + ''.join(bullets))
        self.assertTrue(all(b in ''.join(paragraphs) for b in bullets))
        self.assertNotRegex(narration, r'…|\.{3}')

    def test_short_real_story_does_not_need_padding(self):
        lead = 'DeepSeek 正在灰度测试语音功能，部分用户可以在客户端看到语音入口。'
        detail = '该功能尚未面向所有用户开放，具体开放时间仍需等待官方公布。'
        for paragraphs in ([lead], [lead, detail]):
            bullets, narration = _summary(paragraphs, 'DeepSeek 灰度测试语音功能')
            self.assertEqual(bullets, paragraphs)
            self.assertEqual(narration, 'DeepSeek 灰度测试语音功能。' + ''.join(paragraphs))

    def test_giant_mandatory_attribution_fails_without_truncation(self):
        lead = '据匿名来源透露，' + '这些结果可能来自尚未验证的内部测试，' * 100 + '目前尚无独立证据。'
        with self.assertRaisesRegex(ValueError, '摘要过长'):
            _summary([lead, TEXT], '中文模型训练方法')

    def test_middle_caveat_stays_with_later_performance_claim(self):
        lead = '据研究团队介绍，新模型已经发布，开发者可以查阅技术文档。'
        caveat = '这些结果仅适用于内部测试，尚未经过独立验证。'
        background = '历史资料记录了早期机房的设备采购流程和仓库管理方法。'
        claim = '新模型的性能提高了百分之二十，处理延迟也有所降低。'
        bullets, narration = _summary([lead, caveat, background * 20, claim], '新模型性能提高')
        self.assertIn(lead, narration)
        self.assertIn(caveat, narration)
        self.assertIn(claim, narration)
        self.assertNotIn(background, narration)
        self.assertEqual(narration, '新模型性能提高。' + ''.join(bullets))

    def test_saved_real_articles_keep_core_facts_without_full_read(self):
        fixtures = [('OpenAI 将 Habitat 从 Python 迁移至 Rust：CPU 效率提升 6 倍，服务 10 亿 ChatGPT 用户', 'IT之家 9 月 12 日消息，OpenAI 今日发文，主要介绍了其在线存储平台 Habitat 如何应对产品规模的快速增长，以及从 Python 迁移至 Rust 的工程实践。\nOpenAI 称该平台目前每秒处理超过 7000 万次请求，每周服务超 10 亿用户，管理的数据规模超过 500PB。据介绍，Habitat 已从 2024 年的 Python 客户端库，发展为支撑旗下产品的分布式存储系统。\n据介绍，Habitat 最初是一个与 ChatGPT 主服务器交互的 Python 库，底层连接 Azure Cosmos DB。其目标是让产品工程师无需直接管理数据库，即可完成数据存取。系统负责数据类型识别、路由、授权、加密、序列化及连接池管理等工作。\n随着 OpenAI 产品数量和数据需求增长，Habitat 在 2025 年年中逐渐暴露出客户端架构的局限。每次修改共享库都需要协调数十个服务进行部署，增加了发布复杂度和故障风险。因此，OpenAI 决定将 Habitat 改造为独立服务，集中管理部署、监控和平台功能。\n独立服务还为数据安全提供了统一控制点。OpenAI 可以在 Habitat 中集中执行访问控制、审计日志及底层存储资源权限管理，降低外部、内部及代理程序未经授权访问用户数据的风险。\nOpenAI 最初选择用 Python 开发高吞吐服务，以优先解决平台稳定性和产品开发效率问题。然而，Python 服务在高并发场景下仍面临 CPU 开销、内存开销和网络延迟等挑战，尤其需要控制请求尾延迟。\nHabitat 通过限制并发请求数量、增加 Python 工作进程，以及优化异步任务调度来改善性能。OpenAI 还调整了功能开关配置的刷新策略，减少大规模 JSON 解析对请求处理的影响。\n在连接池方面，OpenAI 发现 Python 的 aiohttp 默认采用 LIFO 连接复用策略，可能导致流量持续集中到响应较慢的服务进程。团队改用 FIFO 连接复用，降低了负载不均衡问题（IT之家注：LIFO 指后进先出，FIFO 指先进先出，两者是常见的队列处理策略）。\nHabitat 采用受限的 NoSQL API，避免客户端执行不可控的 SQL 查询、复杂联表或大范围数据扫描。对于需要复杂查询的场景，OpenAI 通过变更数据捕获（CDC）将数据实时或近实时同步至 Rockset，提供离线分析和搜索能力。\n在 2026 年第二季度，OpenAI 调用 2 名工程师，再加上 Codex 和 GPT-5.5，将 Habitat 服务整体用 Rust 重写。官方数据显示，新的 Rust 服务目前已处理 95% 的生产请求，CPU 效率提升 6 倍，内存效率提升 15 倍，平均延迟和尾延迟也有所降低。\nOpenAI 计划在未来几周内完全弃用 Habitat 的 Python 实现。该公司还表示，后续文章将介绍 Habitat 如何扩展 Azure Cosmos DB 存储层，以及在超过 500PB 数据和每秒 7000 万次请求规模下的多租户可靠性与读性能优化。'), ('第三方公司基于三星 Galaxy Watch 8 打造 Bark Watch 儿童手表，内置 AI 风险监测功能', 'IT之家 9 月 12 日消息，美国科技公司 Bark Technologies 基于三星 Galaxy Watch 8 40mm 版手表进行定制，推出了一款 Bark Watch 儿童手表，面向“已经开始希望获得更多独立性的儿童”，定价为 240 美元 （IT之家注：现汇率约合 1,614 元人民币） 。用户还需要单独购买每月 15 美元 （现汇率约合 100.9 元人民币） 的服务套餐，用于提供蜂窝网络连接以及家长控制功能。\n具体来看，该产品在保留 Galaxy Watch 8 硬件功能的同时，通过软件限制儿童可能接触到的网络风险。不提供社交媒体应用、网页浏览器或手机游戏，也不允许用户不受限制地自行安装应用。Bark 的 AI 平台会在后台运行，对通过短信发送和接收的媒体内容进行分析，一旦发现网络欺凌、情色内容等潜在风险，就会向家长发出提醒。\nBark Technologies 表示，如今儿童在使用互联网和移动设备时可能面临网络欺凌、情色内容以及网络诱骗等风险，而不少儿童智能手表的功能相对基础。因此，本次推出的 Bark Watch 旨在于功能和安全性之间取得平衡，让年龄较大的儿童能够使用更多智能手表功能，同时让家长获得相应的安全管理能力。')]
        for title, source in fixtures:
            self.assertFalse(_model_topic(title))

    def test_default_model_topic_and_nav_labels(self):
        accepted = [
            ('OpenAI 发布 GPT-5.5，新模型数学能力提升', 'GPT'),
            ('ChatGPT 升级语音理解能力', 'ChatGPT'),
            ('Claude 与 Gemini 编程能力评测公布', '模型对比'),
            ('DeepSeek 新模型发布', 'DeepSeek'),
            ('智谱发布 GLM-5，推理能力提升', 'GLM'),
            ('通义千问 Qwen3 多模态模型开源', 'Qwen'),
            ('Kimi K3 上下文能力升级', 'Kimi'),
            ('团队发布新一代大语言模型', '基础模型'),
        ]
        rejected = [
            'OpenAI 完成融资，GPT 团队扩张', 'Claude 公司任命新高管',
            'Gemini 手机发布', 'DeepSeek 订阅套餐升级',
            'ChatGPT 额度提升', 'Qwen 接入办公软件',
            'Sites 发布建站工具，支持 GPT',
            'OpenAI 将 Habitat 从 Python 迁移至 Rust，服务 ChatGPT 用户',
            'AI 安全风险引发讨论', 'GLM 公司财报公布',
            '新款手机发布，多模态模型接入 Gemini',
        ]
        for title, label in accepted:
            self.assertTrue(_model_topic(title), title)
            self.assertEqual(_nav_label(title), label)
        for title in rejected:
            self.assertFalse(_model_topic(title), title)

    def test_compact_nav_and_model_release_main_clause(self):
        self.assertEqual(_nav_label('GPT、Claude、Gemini 评测对比'), '多模型对比')
        self.assertEqual(_nav_label('Claude 与 DeepSeek 评测对比'), '模型对比')
        self.assertEqual(_nav_label('GPT 与 GLM 评测对比'), 'GPT / GLM')
        self.assertEqual(_nav_label('DeepSeek 新模型发布'), 'DeepSeek')
        self.assertTrue(_model_topic('Claude X 模型发布，后续接入办公软件'))
        self.assertTrue(_model_topic('Claude X 模型发布：后续接入浏览器'))
        self.assertFalse(_model_topic('办公软件接入 Claude X 模型，发布新版本'))

    @patch('dailyreport.collect._fetch')
    def test_default_filter_does_not_promote_incidental_body_brand(self, fetch):
        entries = [('Sites 建站工具发布', 'sites'), ('DeepSeek 新模型发布', 'model'),
                   ('OpenAI 公司融资完成', 'finance')]
        feed = '<rss><channel>' + ''.join(
            f'<item><title>{title}</title><description>GPT 新模型能力提升，DeepSeek 评测结果公布。</description><link>https://example.com/{path}</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>'
            for title, path in entries) + '</channel></rss>'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
        result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss', 'ai_only': True}]}, NOW, 24, 8)
        self.assertEqual([s['title'] for s in result['stories']], ['DeepSeek 新模型发布'])
        self.assertEqual(result['stories'][0]['nav_label'], 'DeepSeek')
        self.assertEqual(fetch.call_count, 2)

    def test_three_point_model_summary_keeps_late_caveat(self):
        lead = '据研究团队介绍，DeepSeek 新一代语言模型已经发布，本次更新重点改善中文复杂指令理解和数学推理能力，并公开了对应的评测方法。'
        detail = '模型在公开数学基准上的准确率有所提高，团队同时公布了各项任务使用的提示词和采样配置，开发者可以按照相同条件复现测试结果。'
        caveat = '但这些结果仅适用于报告列出的测试条件，尚未经过第三方独立验证，不能据此推断模型在真实业务中的表现，也不代表已经解决所有幻觉问题。'
        background = '历史资料记录了机房建设数据和旧版采购流程。'
        bullets, narration = _summary([lead, detail, background * 30, caveat], 'DeepSeek 模型能力升级')
        self.assertIn(detail, narration)
        self.assertIn(caveat, narration)
        self.assertNotIn(background, narration)
        self.assertLessEqual(len(bullets), 3)
        self.assertEqual(narration, 'DeepSeek 模型能力升级。' + ''.join(bullets))
        import re
        self.assertTrue(150 <= len(re.findall(r'[\u4e00-\u9fff]', narration)) <= 220)
        self.assertNotRegex(narration, r'…|\.{3}')

    @patch('dailyreport.collect._fetch')
    def test_overlong_summary_is_skipped_with_reason(self, fetch):
        entries = [('DeepSeek 模型能力升级', 'long'), ('Qwen 新模型发布', 'good')]
        feed = '<rss><channel>' + ''.join(f'<item><title>{t}</title><link>https://example.com/{p}</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item>' for t, p in entries) + '</channel></rss>'
        long = '据研究团队今天发布的模型介绍，' + '模型结果仅适用于未经独立验证的内部测试，' * 20 + '无法推及实际业务。'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + (long if url.endswith('long') else TEXT) + '</p></article>'
        result = collect({'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, NOW, 24, 2)
        self.assertEqual([s['nav_label'] for s in result['stories']], ['Qwen'])
        self.assertEqual(len(result['collection_errors']), 1)
        self.assertIn('摘要过长', result['collection_errors'][0])

    def test_shanghai_date_rollover(self):
        with patch('dailyreport.collect._fetch') as fetch:
            fetch.side_effect = ['<rss><channel><item><title>AI模型</title><link>https://example.com/a</link><pubDate>Fri, 11 Sep 2026 16:00:00 GMT</pubDate></item></channel></rss>', '<article><p>' + TEXT + '</p></article>']
            result = collect({'topic_scope': 'all_ai', 'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, datetime(2026, 9, 11, 17, tzinfo=timezone.utc), 24, 1)
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
        result = collect({'topic_scope': 'all_ai', 'sources': [{'name': 'test', 'url': 'https://example.com/rss'}]}, NOW, 24, 100)
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
        config = {'topic_scope': 'all_ai', 'sources': [{'name': '坏源', 'url': 'https://example.com/bad', 'enabled': True, 'ai_only': False}, {'name': '新闻', 'url': 'https://example.com/rss', 'enabled': True, 'ai_only': False}]}
        result = collect(config, NOW, 24, 8)
        self.assertEqual(set(result), {'date', 'window_days', 'title', 'edition_note', 'stories', 'collection_errors'})
        self.assertEqual(result['date'], '2026-09-11')
        story = result['stories'][0]
        self.assertEqual(set(story), {'id', 'category', 'title', 'bullets', 'narration', 'source_name', 'source_url', 'published', 'evidence', 'verification', 'source_text', 'nav_label', 'event_date'})
        self.assertEqual(story['verification'], 'extractive')
        self.assertEqual(story['category'], '模型发布')
        self.assertEqual(story['narration'], story['title'] + '。' + ''.join(story['bullets']))
        self.assertEqual(story['source_text'], TEXT)
        self.assertEqual(story['evidence'], ''.join(story['bullets']))
        self.assertLessEqual(len(story['bullets']), 3)
        self.assertIn('机器抽取', result['edition_note'])
        self.assertEqual(len(result['collection_errors']), 1)
        for bullet in story['bullets']:
            self.assertIn(bullet, TEXT)

    @patch('dailyreport.collect._fetch', return_value='<html>not RSS</html>')
    def test_empty_is_clear_failure(self, fetch):
        with self.assertRaisesRegex(RuntimeError, '没有.*资讯'):
            collect({'topic_scope': 'all_ai', 'sources': [{'name': 'bad', 'url': 'https://example.com', 'enabled': True}]}, NOW, 24, 2)

    @patch('dailyreport.collect._fetch')
    def test_ai_filter_word_boundaries_and_specific_source(self, fetch):
        feed = '<rss><channel><item><title>Daily railway update</title><link>https://example.com/a</link><pubDate>Fri, 11 Sep 2026 11:00:00 GMT</pubDate></item></channel></rss>'
        fetch.side_effect = lambda url: feed if url.endswith('rss') else '<article><p>' + TEXT + '</p></article>'
        source = dict(name='test', url='https://example.com/rss', enabled=True, ai_only=False)
        with self.assertRaises(RuntimeError):
            collect({'topic_scope': 'all_ai', 'sources': [source]}, NOW, 24, 1)
        source['ai_only'] = True
        self.assertEqual(len(collect({'topic_scope': 'all_ai', 'sources': [source]}, NOW, 24, 1)['stories']), 1)


if __name__ == '__main__':
    unittest.main()
