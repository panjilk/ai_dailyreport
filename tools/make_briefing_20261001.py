# -*- coding: utf-8 -*-
"""2026-10-01 期 AI 日报稿件（Hermes 按 7 条规则手写）。窗口：北京 9/27 00:00 起。"""
import json, re
from pathlib import Path

CATEGORIES = ['要闻', '模型发布', '开发生态', '产品应用', '技术洞察', '行业动态']
S = []

S.append(dict(
    title="Google 发布 Gemini 4 Argon 模型",
    category="模型发布", nav_label="Gemini 4 Argon", source_name="Google DeepMind 官方",
    source_url="https://deepmind.google/blog/gemini-4-argon-our-next-era-of-frontier-intelligence/",
    published="2026-09-30", event_date="2026-09-30",
    event_date_evidence="Google DeepMind 官方博客 Sep 30, 2026；IT之家 10月1日 6:57（北京时间）报道基准与定价",
    verification="official_announcement_plus_media_report_vendor_benchmarks_flagged",
    supporting_sources=[
        dict(name="IT之家：Argon 基准与价格", url="https://www.ithome.com/1/008/953.htm"),
        dict(name="TechCrunch：Google releases Gemini 4 Argon", url="https://techcrunch.com/2026/09/30/google-releases-gemini-4-argon-called-its-most-powerful-model-yet/"),
    ],
    bullets=[
        "Google DeepMind 在 9月30日发布 Gemini 4 Argon，官方称是迄今最先进的模型，主打长流程软件工程、金融法律等企业知识和网络安全防御，但目前没有对公众开放。",
        "它单次输出上限约一百万 tokens，是此前六万四千的十五倍以上；谷歌给出的长周期代码基准 DeepSWE v1.1 得分 77.9%，高于 Claude Opus 5.5 的 74.2% 和 GPT-6 Astra 的 74.1%。",
        "限制是分阶段开放：第一阶段只给 Fairwind 计划里受信任的防守方，并按美国政府预发布流程走；成绩全部出自谷歌自己，没有第三方复测，起步价每百万输入 2 美元、输出 10 美元。",
    ],
    video_bullets=["谷歌发布 Gemini 4 Argon，单次能输出约一百万 tokens，官方公布的代码基准超过 Claude Opus 5.5，但现在只开放给受信任的网络安全防御者。"],
))

S.append(dict(
    title="蚂蚁百灵发布 Ling-3.1-flash",
    category="模型发布", nav_label="Ling-3.1-flash", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/907.htm",
    published="2026-09-30T12:43:48+08:00", event_date="2026-09-30",
    event_date_evidence="IT之家 9月30日 消息（蚂蚁百灵当日发布）；源报道标注发布时间 2026-09-30T12:43:48+08:00",
    verification="media_report_official_claims_no_benchmark_numbers_given",
    bullets=[
        "蚂蚁百灵在 9月30日发布 Ling-3.1-flash，总参数约 5600 亿、每个 token 只激活约 250 亿，上下文窗口上限一百万，可容纳更长的文档、代码和任务历史。",
        "官方称研发时围绕通用智能体、搜索、日常办公和软件研发优化，并在医疗、金融和材料科学场景持续提升；目前开放两周免费体验，免费期内服务长度限制在 256K。",
        "限制是免费期结束后才计划开放一百万上下文，同时才计划开源权重，时间表都没定；报道只附了评测图表，没有给出可以逐条核对的分数。",
    ],
    video_bullets=["蚂蚁百灵发布 Ling-3.1-flash，总参数约 5600 亿但每个词元只激活 250 亿，上下文上限一百万，先开放两周免费体验。"],
))

S.append(dict(
    title="OpenAI 与新思共研 GPT-Synopsys",
    category="模型发布", nav_label="GPT-Synopsys", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/968.htm",
    published="2026-10-01T08:24:51+08:00", event_date="2026-10-01",
    event_date_evidence="Synopsys 当地时间 9月30日 宣布；IT之家 10月1日 8:24（北京时间）报道",
    verification="media_report_of_vendor_announcement_model_not_yet_released",
    bullets=[
        "Synopsys 在当地时间 9月30日宣布与 OpenAI 达成多年期战略合作，共同开发 GPT-Synopsys，把模型能力接进 Synopsys 的芯片设计工具链。",
        "目标是让模型成为 EDA 工具的原生专家用户：工程师把设计目标交给调用工具的智能体，由它解读结果、改设计、反复迭代，最后给出可审核的验证结果并优化功耗、性能与面积。",
        "限制是模型仍在联合开发，没有发布时间和可用范围；合作采用共享收益框架，OpenAI 获得新思可信 EDA 工具授权，属于垂直行业定制，不是一次通用模型升级。",
    ],
    video_bullets=["OpenAI 与芯片设计软件公司新思达成多年合作，共同开发 GPT-Synopsys，让模型直接操作 EDA 工具做设计迭代，目前仍在开发中。"],
))

S.append(dict(
    title="DeepSeek 开源昇腾基础组件",
    category="开发生态", nav_label="DeepSeek", source_name="量子位",
    source_url="https://www.qbitai.com/2026/09/499263.html",
    published="2026-09-30T10:53:17+08:00", event_date="2026-09-30",
    event_date_evidence="量子位 9月30日 10:53 报道（华为供稿），当日 DeepSeek 开源",
    verification="vendor_supplied_article_open_source_repos_linked_benchmarks_vendor_measured",
    bullets=[
        "DeepSeek 在 9月30日开源面向华为昇腾平台的基础设施组件，包括 TileLang 编译工具、DeepGEMM、FlashMLA、TileKernel 等算子库和 DeepEP 通信库，与此前的 GPU 版一一对应。",
        "华为提供昇腾接口与 UBL128 超节点组网，实测互联带宽 Dispatch 375 GB/s、Combine 347 GB/s；在 EP32 部署下，DeepSeek-V4.1-Flash 每卡输出吞吐可达每秒 2469 到 5102 个 token。",
        "限制是性能数字来自双方自己的离线测试，不包含服务调度和框架负载均衡的影响；这篇报道由华为供稿、量子位转载，不是独立第三方评测。",
    ],
    video_bullets=["DeepSeek 开源面向华为昇腾的算子和通信组件，和之前的 GPU 版一一对应，在昇腾超节点上实测互联带宽接近硬件上限。"],
))

S.append(dict(
    title="OpenAI 称打断模型蒸馏行动",
    category="要闻", nav_label="OpenAI", source_name="OpenAI 官方",
    source_url="https://openai.com/index/disrupting-a-coordinated-model-distillation-campaign",
    published="2026-09-30", event_date="2026-09-30",
    event_date_evidence="OpenAI 官方安全公告 Sep 30, 2026；Unite.AI 9月30日 报道细节与归因",
    verification="official_security_post_plus_media_summary_attribution_uncertain_flagged",
    supporting_sources=[dict(name="Unite.AI：蒸馏行动细节", url="https://www.unite.ai/openai-disrupts-coordinated-model-reasoning-extraction-campaign/")],
    bullets=[
        "OpenAI 在 9月30日发布安全公告，称已打断一场协同的模型蒸馏行动：对方没有破解加密或入侵数据库，而是通过操纵对话，让受保护的推理过程以可见形式被复制出来。",
        "公告称这类活动最早出现在 7月1日，7月24日至 25日出现高峰，两天内四千多名用户发出约一万六千次相关请求；OpenAI 把核心活动归因于与月之暗面有关联的个人。",
        "限制是统计的是尝试次数而不是成功提取，归因也留有余地；美国国安局、网络安全局和联邦调查局在 9月8日的联合公告中称，月之暗面自 2025 年中起对多家美国前沿公司做过广泛蒸馏。",
    ],
    video_bullets=["OpenAI 说打断了一场提取模型推理的协同行动，并把核心活动归因于与月之暗面有关联的个人，对方用操纵对话的方式复制推理过程。"],
))

S.append(dict(
    title="OpenAI 的 Decisions API 被指克隆 Jev",
    category="开发生态", nav_label="Decisions API", source_name="TechCrunch AI",
    source_url="https://techcrunch.com/2026/09/30/openais-jev-clone-could-help-the-frontier-lab-stop-its-swarming-agents/",
    published="2026-09-30T19:00:00+00:00", event_date="2026-09-30",
    event_date_evidence="TechCrunch 9月30日 12:00 PDT（19:00 UTC）报道，比较 DevDay 的 Decisions API 与 TypeSafe 的 Jev",
    verification="media_report_with_named_people_vendor_comparison_unverified",
    bullets=[
        "TechCrunch 在 9月30日报道，开发者日上发布的 Decisions API 与 TypeSafe AI 本月推出的 Jev 属于同一类产品：都给模型一组预设选项，让它便宜又快速地输出概率或选择。",
        "TypeSafe 首席执行官是前 OpenAI 工程师、强化学习共同发明人，他在社交媒体上调侃“克隆战争”开始，并称 OpenAI 的兴趣说明用快速直觉方式做软件自动化是趋势。",
        "限制是 Decisions API 目前只是有限预览，报道称还没看到开发者实测；两家产品相似度不明，这类快决策模型的输出是否校准、能不能对上真实需求也还没有答案。",
    ],
    video_bullets=["OpenAI 的 Decisions API 被指与创业公司 TypeSafe 的 Jev 是同类产品，对方 CEO 调侃克隆战争开始，这类快决策模型正被用来监控 AI 代理。"],
))

S.append(dict(
    title="CoreWeave 上线 Vera Rubin 系统",
    category="产品应用", nav_label="Vera Rubin", source_name="NVIDIA 官方博客",
    source_url="https://blogs.nvidia.com/blog/coreweave-agentic-ai-vera-rubin/",
    published="2026-09-30T15:00:00+00:00", event_date="2026-09-30",
    event_date_evidence="NVIDIA 官方博客 Sep 30, 2026（CoreWeave Fully Connected 大会当日）",
    verification="official_vendor_blog_early_customer_benchmark_not_independently_reviewed",
    bullets=[
        "在 9月30日的 CoreWeave Fully Connected 大会上，CoreWeave 宣布 NVIDIA Vera Rubin NVL72 系统与 Spectrum-X 102.4T 以太网可用，并推出号称首款为 AI 代理设计的 CPU Vera。",
        "应用实验室 Cognition 是首个在生产环境跑 Vera Rubin 的客户：在真实软件工程任务上，SWE-2 推理的词元吞吐比上一代 GB200 NVL72 最高提升 4.8 倍。",
        "限制是这些数字来自 Cognition 与 CoreWeave 的早期测试，由 NVIDIA 官方博客发布，没有独立复测；新系统与 Forge 环境目前只面向早期访问客户。",
    ],
    video_bullets=["CoreWeave 上线 NVIDIA Vera Rubin NVL72 系统，并推出号称首款为 AI 代理设计的 CPU，首个生产客户 Devin 母公司实测吞吐提升最多 4.8 倍。"],
))

S.append(dict(
    title="Meta Muse 22 天下载破 500 万",
    category="产品应用", nav_label="Meta Muse", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/959.htm",
    published="2026-10-01T07:45:52+08:00", event_date="2026-09-30",
    event_date_evidence="IT之家 10月1日 7:45 报道 Sensor Tower 数据（9月30日 达成 500 万下载）",
    verification="third_party_estimator_data_usage_not_retention_flagged",
    bullets=[
        "据调查机构 Sensor Tower，Meta 的智能体助手 Muse 上线 22 天、也就是 9月30日下载量突破 500 万次，成为美国 App Store 免费榜第一，并连续 12 天保持榜首。",
        "它比 ChatGPT 的 56 天、Grok 的 103 天和 Claude 的 492 天都快；Muse 能替用户浏览网页、发邮件、网购、填表和订行程，Meta 从 9月16日 起加大投放，当日下载量环比涨 73%。",
        "限制是下载量只是第三方估算，不等于活跃或留存；过去两周 Muse 占到 Meta 自有广告展示的最高一半，说明这波增长有很强的买量成分。",
    ],
    video_bullets=["Meta 的智能体助手 Muse 上线 22 天在美国下载破 500 万次，比 ChatGPT 快一倍多，不过增长很大程度靠 Meta 自家广告投放。"],
))

S.append(dict(
    title="Hugging Face 上线开源 TTS 榜单",
    category="技术洞察", nav_label="TTS 榜单", source_name="Hugging Face 官方博客",
    source_url="https://huggingface.co/blog/open-tts-leaderboard",
    published="2026-09-30", event_date="2026-09-30",
    event_date_evidence="Hugging Face 官方博客 Published September 30, 2026",
    verification="official_benchmark_announcement_objective_metrics_limits_stated_by_authors",
    bullets=[
        "Hugging Face 在 9月30日发布 Open TTS Leaderboard，用客观指标评测语音合成：可懂度看词错率、速度看实时倍率，音色相似度用说话人向量比对，把评测周期从几周压到几小时。",
        "背景是开源语音模型已超过八千个，而人工投票式榜单跟不上：Artificial Analysis 上的 92 个模型里只有 16 个是开放权重，开源模型长期被低估。",
        "限制是官方明确说它不能取代人耳偏好：词错率和音色相似度都无法直接反映自然度、表现力和听感，定位是人工榜单的补充而不是替代。",
    ],
    video_bullets=["Hugging Face 上线开源语音合成榜单，用词错率、实时倍率和音色相似度三项客观指标评测，几小时就能出结果，但官方说它不能代替人耳听感。"],
))

briefing = dict(
    date="2026-10-01",
    window_days=5,
    edition_start_date="2026-09-27",
    title="AI 日报 · 2026-10-01",
    edition_note=("本期 9 条覆盖 9月30日 到 10月1日：Gemini 4 Argon 与蚂蚁 Ling-3.1-flash 两个具名模型发布，"
                  "OpenAI 与新思共研芯片设计模型 GPT-Synopsys，DeepSeek 开源昇腾基础组件，"
                  "另有 OpenAI 打断模型蒸馏行动（点名与月之暗面有关联的个人）、Decisions API 与 Jev 的克隆之争、"
                  "NVIDIA Vera Rubin 上云、Meta Muse 22 天破 500 万下载，以及 Hugging Face 的客观指标 TTS 榜单。"
                  "厂商自评、第三方估算与匿名信源的限制均在画面要点注明。"),
    stories=S,
)

problems = []
for s in S:
    t = s['title']
    if len(t) > 40:
        problems.append(f"标题过长({len(t)}): {t}")
    if s['category'] not in CATEGORIES:
        problems.append(f"分类非法: {s['category']}")
    for b in s['bullets']:
        first = re.split(r'[，,；;：]', b)[0]
        if len(first) > 76:
            problems.append(f"bullet 首句 {len(first)}>76: {b[:26]}")
    total = sum(len(b) for b in s['bullets'])
    if total > 290:
        problems.append(f"bullets 总长 {total} 偏大: {t}")
    vb = s['video_bullets'][0]
    if not (40 <= len(vb) <= 100):
        problems.append(f"口播 {len(vb)} 字: {t}")
    if re.search(r'https?://|来源|…|\.\.\.', vb):
        problems.append(f"口播含禁词: {t}")

print(f"stories: {len(S)}")
for s in S:
    print(f"  {s['nav_label']:<15} | 标题{len(s['title']):>2} | 要点总{sum(len(b) for b in s['bullets']):>3}字（最长 {max(len(b) for b in s['bullets'])}）| 口播{len(s['video_bullets'][0]):>2}字")
print("自查问题:", problems or "无")

out = Path('data/briefing-2026-10-01-models.json')
out.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding='utf-8')
print("写入:", out)
