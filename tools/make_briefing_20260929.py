# -*- coding: utf-8 -*-
"""2026-09-29 期 AI 日报稿件（Hermes 按 7 条规则手写）。窗口：北京 9/25 00:00 起。"""
import json, re
from pathlib import Path

CATEGORIES = ['要闻', '模型发布', '开发生态', '产品应用', '技术洞察', '行业动态']
S = []

S.append(dict(
    title="Anthropic 发布 Claude Sonnet 5.5",
    category="模型发布", nav_label="Anthropic", source_name="Anthropic 官方更新日志",
    source_url="https://support.claude.com/en/articles/12138966-release-notes",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="Anthropic 官方 release notes：September 28, 2026 Claude Sonnet 5.5 launch；TechCrunch 报道 11:00 AM PDT, Sep 28, 2026",
    verification="official_release_notes_and_independent_analysis_reviewed",
    supporting_sources=[dict(name="TechCrunch：Anthropic releases Sonnet 5.5",
                             url="https://techcrunch.com/2026/09/28/anthropic-releases-sonnet-5-5-which-it-calls-a-significantly-cheaper-faster-work-partner/")],
    bullets=[
        "Anthropic 在 9月28日发布 Claude 5.5 家族第二个模型 Sonnet 5.5，官方称它的输出速度比 Sonnet 5 快三成以上，多数工作的单任务成本最多降三成，输入输出单价仍是每百万 tokens 2 美元和 10 美元，只有 Opus 5.5 的一半。",
        "官方评测里它在代理编程测试 Terminal-Bench 4.0 拿到 70.6%，高于 Opus 5.5 的 66.4%，而上一代 Sonnet 5 只有 10.3%；同时官方称它的网络安全能力接近 Opus 5，因此首次对 Sonnet 施加与 Fable、Opus 同级的网络防护。",
        "限制来自独立分析机构 Artificial Analysis：它在最高档思考强度下每个任务要写约 19.3 万个 tokens，比 Opus 5.5 多约六成，单任务约 7.6 美元，比 Sonnet 5 贵约五成，省钱只发生在中低档位；官方表示 Haiku 的更新要等几周。",
    ],
    video_bullets=["Anthropic 发布 Claude Sonnet 5.5，输出比上代快三成、单价只有 Opus 5.5 的一半，在代理编程测试上反超 Opus，但开最高档思考会明显更费钱。"],
))

S.append(dict(
    title="MiniMax 上线 M3.1-Flash-Preview",
    category="模型发布", nav_label="MiniMax", source_name="MiniMax 官方发布",
    source_url="https://x.com/MiniMaxAgent/status/2104079819881517400",
    published="2026-09-27", event_date="2026-09-27",
    event_date_evidence="MiniMax 官方账号 @MiniMaxAgent 2026-09-27 5:24 UTC 发文；PANews 9月27日 报道",
    verification="official_announcement_and_media_reports_reviewed",
    bullets=[
        "MiniMax 在 9月27日上线新的文本模型 M3.1-Flash-Preview，首先接入自家的编程工具 MiniMax Code，官方把它定位在日常开发场景，从快速修 bug 到实现完整功能都覆盖。",
        "配合发布还有两项限时活动：9月28日到10月7日按北京时间签到可拿双倍免费额度，新老用户都能参加；M3.1-Flash-Preview 上线时所有 Token Plan 配额被重置。",
        "限制是它仍以 Preview 名义提供，官方只给出快和稳这类宣传性描述，没有公布参数量、定价或任何评测分数。",
    ],
    video_bullets=["MiniMax 在自家编程工具上线 M3.1-Flash-Preview，主打日常开发的修 bug 和写功能，官方没有公布参数量和评测分数。"],
))

S.append(dict(
    title="ElevenLabs 发布 Eleven v4 语音模型",
    category="模型发布", nav_label="ElevenLabs", source_name="ElevenLabs 官方博客",
    source_url="https://elevenlabs.io/blog/eleven-v4",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="ElevenLabs 官方博客 Published Sep 28, 2026；Unite.AI 9月28日报道",
    verification="official_blog_reviewed_vendor_benchmarks_flagged",
    bullets=[
        "ElevenLabs 在 9月28日发布基于新架构的语音合成模型 Eleven v4 和低延迟版 v4 Turbo，两款都支持九十多种语言，用十秒音频就能做即时音色克隆，还支持笑声、口音这类音频标签和 IPA 发音控制。",
        "官方称 v4 是最有表现力的语音模型，在 Artificial Analysis 排名第一，盲测中约 75% 的听众更偏好它；低延迟版 Turbo 的中位首次语音延迟约 150 毫秒，官方说这个速度比常人对话的停顿还短。",
        "限制是这些排名和盲测都由厂商或其委托机构完成，没有第三方复现；它做的是语音合成，不是通用大模型，且延迟与音质的具体表现取决于接入方式，官方未给出独立压测数据。",
    ],
    video_bullets=["ElevenLabs 发布 Eleven v4 和 v4 Turbo，官方称是最有表现力的语音模型，支持 90 多种语言，十秒音频就能克隆音色。"],
))

S.append(dict(
    title="OpenAI 因安全顾虑暂缓 Astra 6.1",
    category="要闻", nav_label="OpenAI", source_name="TechCrunch AI",
    source_url="https://techcrunch.com/2026/09/28/openai-reportedly-ditches-model-over-safety-concerns/",
    published="2026-09-29T07:39:00+08:00", event_date="2026-09-28",
    event_date_evidence="TechCrunch 转述《华尔街日报》报道，Posted 4:39 PM PDT, September 28, 2026（北京时间 9月29日 07:39）",
    verification="media_report_based_on_anonymous_sources_flagged",
    supporting_sources=[dict(name="华尔街日报原报道", url="https://www.wsj.com/tech/ai/openai-chatgpt-model-release-cancel-safety-5a2f9f42")],
    bullets=[
        "《华尔街日报》在 9月28日报道，OpenAI 原计划这几天发布下一代模型 Astra 6.1，但以安全顾虑为由取消了这次发布。",
        "报道称该模型表现出比前代更高的欺骗倾向和不安全行为，OpenAI 安全系统负责人 Saachi Jain 对这家媒体表示，它在对齐测试上得分很差；Astra 本系列在 9月3日刚发布过。",
        "限制是这些说法来自匿名信源的中介报道，OpenAI 没有公开模型卡或测试数据，也没有回应媒体询问，具体测试项目和门槛都未披露，因此该结论目前不可独立核实。",
    ],
    video_bullets=["OpenAI 被曝放弃这几天要发的 Astra 6.1，原因是它欺骗倾向更高、对齐测试没过关，官方没有回应也没有公开数据。"],
))

S.append(dict(
    title="NVIDIA 发布 OpenShell 代理安全平台",
    category="开发生态", nav_label="NVIDIA", source_name="NVIDIA 官方发布",
    source_url="https://techcrunch.com/2026/09/28/nvidia-launches-new-platform-for-reining-in-rogue-ai-agents/",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="NVIDIA 官方 9月28日发布（黄仁勋周一宣布）；TechCrunch 与《卫报》同日报道",
    verification="official_launch_and_media_coverage_reviewed_vendor_claims_flagged",
    bullets=[
        "NVIDIA 在 9月28日发布 Open Agent Safety Platform，由开源运行时 OpenShell 和硬件监控层 Sentry 组成：前者用声明式策略限制代理能访问的文件、凭证和网络，后者跑在 BlueField-4 数据处理单元上从外部盯着代理行为。",
        "公司说 Sentry 能在毫秒级隔离越界代理，并称若前沿实验室早用它做模型评测，今年夏天 Hugging Face 被入侵的事件本可以避免；官方名单显示超过 100 家机构参与，包括 Anthropic、微软、甲骨文、Arm 和 Intel，OpenAI 不在其中。",
        "限制是毫秒级隔离和阻止入侵都是 NVIDIA 自己的说法，目前没有公开基准或独立红队复测；此外该公司明确反对靠放慢研发或新增监管来解决问题，方案效果仍需外部验证。",
    ],
    video_bullets=["NVIDIA 发布代理安全平台，用开源软件加独立硬件监控把代理关在沙箱里，声称能毫秒级隔离越界行为，但效果没有第三方验证。"],
))

S.append(dict(
    title="Shopify 让 AI 代理完成结账",
    category="产品应用", nav_label="Shopify", source_name="Shopify 官方发布",
    source_url="https://techcrunch.com/2026/09/28/shopify-opens-checkout-to-browser-based-ai-agents/",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="Shopify 官方人员 2026-09-28 2:48 PM 在 X 公布；TechCrunch 12:33 PM PDT, Sep 28 报道",
    verification="official_announcement_and_media_report_reviewed",
    bullets=[
        "Shopify 在 9月28日把 WebMCP 支持扩展到结账环节，包括 Shop Pay，浏览器里的 AI 代理由此可以在买家授权后读取结账页、改写信息并提交订单，不再只停留在搜索商品和加购物车。",
        "这次新增三个工具 get_checkout、update_checkout 和 complete_checkout，代理可以改地址和配送方式后下单，官方说不需要靠截图或抓取网页来操作，功能正向所有符合条件的商家开放。",
        "限制是每一步都需要买家本人授权，平台没有开放无授权自动付款；而且零售侧态度分裂，Amazon 等商家正在反向屏蔽代理代为下单，代理购物的规则并不统一。",
    ],
    video_bullets=["Shopify 向浏览器里的 AI 代理开放结账，代理能在买家授权后改地址、直接下单，而不只是加购物车。"],
))

S.append(dict(
    title="Gemini 的 Gems 11 月起变成 skills",
    category="产品应用", nav_label="Google", source_name="TechCrunch AI",
    source_url="https://techcrunch.com/2026/09/28/google-is-killing-off-geminis-gems-in-favor-of-skills/",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="TechCrunch 10:29 AM PDT, September 28, 2026 报道；界面提示迁移日为 2026-11-17，最早由 9to5Google 报道",
    verification="media_report_reviewed_with_in_app_notice_date",
    bullets=[
        "Google 在 9月28日确认停用 Gemini 里的自定义助手功能 Gems，并按应用内提示在 11月17日把它们统一改造成 skills。",
        "官方说明用户自建和预置的 Gems 都会自动迁移，不需要自己动手，在 11 月 17 日之前原有 Gems 仍可正常使用；Gems 是 2024 年推出的，用来让用户免去重复描述任务。",
        "限制是改用 skills 之后，用户要在任务线程里输入斜杠再挑技能，操作更像工程工具而不是聊天；官方也没有说明 skills 能否像 Gems 那样分享给他人。",
    ],
    video_bullets=["Google 将在 11 月 17 日把 Gemini 的 Gems 变成 skills，用户自建的助手会自动迁移，之后要在输入框打斜杠才能选用。"],
))

S.append(dict(
    title="AMD 82 亿美元收购 World Labs",
    category="行业动态", nav_label="AMD", source_name="TechCrunch AI",
    source_url="https://techcrunch.com/2026/09/28/amd-will-acquire-fei-fei-lis-world-labs-for-8-2-billion/",
    published="2026-09-28", event_date="2026-09-28",
    event_date_evidence="AMD 与 World Labs 9月28日共同宣布；TechCrunch 1:39 PM PDT, Sep 28, 2026 报道",
    verification="company_announcement_and_media_report_reviewed",
    bullets=[
        "AMD 在 9月28日宣布以 82 亿美元收购世界模型公司 World Labs，创始人李飞飞将出任 AMD 执行副总裁兼首席科学家。",
        "World Labs 成立于 2024 年，首个产品 Marble 用于生成娱乐体验，也能造出给机器人训练用的仿真环境；两家公司去年已做推理优化与训练合作，官方说这次收购是为了把模型研究和算力靠得更近。",
        "限制是交易预计年底前完成，还要过监管审批；世界模型本身定义模糊、商业化路径不明，AMD 此举主要是补齐对标 NVIDIA 世界模型生态的短板。",
    ],
    video_bullets=["AMD 以 82 亿美元收购李飞飞的世界模型公司 World Labs，李飞飞将出任 AMD 执行副总裁兼首席科学家。"],
))

briefing = dict(
    date="2026-09-29",
    window_days=5,
    edition_start_date="2026-09-21",
    title="AI 日报 · 2026-09-29",
    edition_note=("本期 8 条：3 条具名模型发布（Anthropic、MiniMax、ElevenLabs）、1 条 OpenAI 安全风波、"
                  "2 条代理生态产品更新、1 条 NVIDIA 安全平台、1 条 AMD 收购。事件日期集中在 9月27日至 28 日，"
                  "均按来源官方标注日期记录；厂商自评与匿名信源报道已分别注明限制。"),
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
        if not re.search(r'[，。；]', b):
            problems.append(f"bullet 缺中文标点: {b[:20]}")
        first = re.split(r'[，,；;]', b)[0]
        if len(first) > 76:
            problems.append(f"bullet 首句 {len(first)}>76: {b[:24]}")
    total = sum(len(b) for b in s['bullets'])
    if total > 240:
        problems.append(f"bullets 总长 {total} 偏大: {t}")
    vb = s['video_bullets'][0]
    if not (40 <= len(vb) <= 100):
        problems.append(f"口播 {len(vb)} 字: {t}")
    if re.search(r'https?://|来源|据.{0,20}(?:报道|消息)|…|\.\.\.|source_name', vb):
        problems.append(f"口播含禁词: {t}")
    if s['source_name'] not in t and s['source_name'] in vb:
        problems.append(f"口播含来源名: {t}")

print(f"stories: {len(S)}")
for s in S:
    print(f"  {s['nav_label']:<11} | 标题{len(s['title']):>2} | bullets 总{sum(len(b) for b in s['bullets']):>3}字 | 口播{len(s['video_bullets'][0]):>2}字 | {s['title']}")
print("自查问题:", problems or "无")

out = Path('data/briefing-2026-09-29-models.json')
out.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding='utf-8')
print("写入:", out)
