# -*- coding: utf-8 -*-
"""2026-09-30 期 AI 日报稿件（Hermes 按 7 条规则手写）。主线：OpenAI DevDay 2026（9/29）。窗口：北京 9/26 00:00 起。"""
import json, re
from pathlib import Path

CATEGORIES = ['要闻', '模型发布', '开发生态', '产品应用', '技术洞察', '行业动态']
S = []

S.append(dict(
    title="OpenAI 发布 GPT-6.1 Sol 模型",
    category="模型发布", nav_label="GPT-6.1 Sol", source_name="OpenAI 官方发布",
    source_url="https://openai.com/index/introducing-gpt-6-1-sol/",
    published="2026-09-29", event_date="2026-09-29",
    event_date_evidence="OpenAI 官方 9月29日发布 Introducing GPT-6.1 Sol；IT之家 9月30日（北京时间）报道定价细节",
    verification="official_announcement_and_pricing_page_reviewed_vendor_benchmarks_flagged",
    supporting_sources=[dict(name="IT之家：GPT-6.1 Sol 定价与评测", url="https://www.ithome.com/1/008/527.htm")],
    bullets=[
        "OpenAI 在 9月29日的开发者日活动上发布 GPT-6.1 Sol，是 GPT-6 Sol 的升级版：在智能体编程、电脑操作和专业工作流上接近旗舰 GPT-6 Astra，标准输入输出价格只有 Astra 的五分之一。",
        "短上下文的标准档每百万 tokens 输入 2 美元、输出 10 美元，缓存输入 0.1 美元、比 GPT-6 Sol 低一半；批量与弹性档再打五折，另有加价优先处理的快速档，长上下文价格翻倍。",
        "限制是评测数据全部来自 OpenAI 自己：事实错误率在低推理强度下从 11.4% 降到 7.7%，官方称各推理档与 Astra 的差距都在 1.9% 以内，尚无第三方复测；API 名为 gpt-6.1-sol。",
    ],
    video_bullets=["OpenAI 发布 GPT-6.1 Sol，性能接近旗舰 Astra，输入输出价格只有它的五分之一，缓存费用比上一代低一半，评测数据来自官方自己。"],
))

S.append(dict(
    title="OpenAI 推出 Dots 常驻代理",
    category="产品应用", nav_label="Dots", source_name="OpenAI 官方发布",
    source_url="https://openai.com/index/introducing-dots/",
    published="2026-09-29", event_date="2026-09-29",
    event_date_evidence="OpenAI 官方 9月29日发布 Introducing dots；TechCrunch 9月29日报道",
    verification="official_announcement_and_media_report_reviewed",
    supporting_sources=[dict(name="TechCrunch：OpenAI launches Dots", url="https://techcrunch.com/2026/09/29/openai-launches-dots-its-bubbly-agentic-avatar/")],
    bullets=[
        "OpenAI 在 9月29日发布 Dots：一类始终在线的个人代理，由 GPT-6 Astra 驱动，每个 Dot 有自己的云电脑和浏览器，通过插件可连接四千多个应用，可以长期朝用户设定的目标干活。",
        "Dots 会在后台对已连接的应用做只读的主动研究，执行动作前要用户批准；可以在 Slack、Teams 等工具里对话，官方称若监控系统发现安全顾虑，可以暂停或终止这个代理的工作。",
        "限制是企业、教育和医疗场景默认关闭，要管理员手动开启；目前只对符合条件的 Pro 与 Business Premium 市场开放，代理的身份与凭据仍依赖既有系统来管理。",
    ],
    video_bullets=["OpenAI 发布 Dots 常驻代理，每个都有自己的云电脑和浏览器，能连四千多个应用长期干活，动手前要用户批准。"],
))

S.append(dict(
    title="OpenAI 推出 Ultrafast 速度档与 Pro 500",
    category="产品应用", nav_label="Ultrafast", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/524.htm",
    published="2026-09-29T17:43:14+00:00", event_date="2026-09-29",
    event_date_evidence="OpenAI 9月29日 DevDay 发布；IT之家 9月30日（北京时间）报道；The Decoder 9月29日同日报道价格",
    verification="media_report_and_official_pricing_reviewed",
    supporting_sources=[dict(name="The Decoder：Ultrafast 六倍定价", url="https://the-decoder.com/openai-expands-codex-and-its-api-at-devday-with-security-scans-a-decisions-api-and-ultrafast/")],
    bullets=[
        "OpenAI 在 9月29日推出 Ultrafast 速度档：它不是新模型，而是优先算力档，官方称在 Codex 里词元生成最高快八倍、API 最高快六倍，实测约每秒三百个词元，目前只对 GPT-6 Astra 开放。",
        "代价在价格：API 端按标准价的六倍计费，Astra 相当于每百万 tokens 输入 60 美元、输出 300 美元；同时上线每月 500 美元的 Pro 500 订阅，包含 Ultrafast 与最高的用量额度。",
        "限制是快的是生成速度，不等于整个任务快八倍，官方还说明了上线期的速率限制；另外新的 Pro 200 订阅额度下调，GPT-6 Pro 消息从每周 200 条减到 100 条，老用户有过渡期。",
    ],
    video_bullets=["OpenAI 推出 Ultrafast 速度档，Codex 里每秒能生成三百个词元，但价格是标准价的六倍，还要搭配每月五百美元的订阅。"],
))

S.append(dict(
    title="OpenAI 发布 Decisions API",
    category="开发生态", nav_label="Decisions API", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/531.htm",
    published="2026-09-30T02:06:51+08:00", event_date="2026-09-29",
    event_date_evidence="OpenAI 9月29日 DevDay 发布；IT之家 9月30日（北京时间）2:06 报道；官方 Recap 同日",
    verification="media_report_and_official_recap_reviewed",
    bullets=[
        "OpenAI 在 9月29日发布 Decisions API，走的是另一条路：开发者给出一组有限的候选答案和上下文，模型只回一个答案，用来做内容分类、请求路由，或者决定代理的下一步动作。",
        "官方称它基于低成本的 GPT-6 Luna，做一次决定约一百五十毫秒，比通过常规 API 调用 Luna 快约十倍，并且支持图片输入；这个快决策方向由一家前 OpenAI 研究员创办的公司带火。",
        "限制是它现在还只是有限预览，官方说未来几天才广泛开放，定价也没公布；第三方早期测试显示它在部分任务上比同类模型又快又准，但在更广的评测里落后。",
    ],
    video_bullets=["OpenAI 发布 Decisions API，用 GPT-6 Luna 做单步判定，一百五十毫秒出答案，比常规调用快十倍，目前还是有限预览。"],
))

S.append(dict(
    title="Codex 新增云环境与安全扫描",
    category="开发生态", nav_label="Codex", source_name="The Decoder",
    source_url="https://the-decoder.com/openai-expands-codex-and-its-api-at-devday-with-security-scans-a-decisions-api-and-ultrafast/",
    published="2026-09-29", event_date="2026-09-29",
    event_date_evidence="OpenAI 9月29日 DevDay 发布（官方新闻稿）；The Decoder 9月29日报道",
    verification="media_report_based_on_official_press_release_reviewed",
    bullets=[
        "OpenAI 在 9月29日给 Codex 做了一次大更新：新增可复用的云开发环境，团队能共享设置与权限，任务放在云端跑，开发者用电脑或手机回来接着处理。",
        "同批更新还有新版 Codex 命令行工具，加入语音对话、代理跟踪视图和内置 worktrees；新的 Codex Security Cloud 会按需或定时扫描代码仓库，过滤重复结果并在云端准备修复。",
        "限制是安全扫描面向 Pro、Business、Enterprise 与 Edu 计划，给出的修复仍要人来确认；Agents API 新增的电脑操作和 AWS 上的托管代理目前都还是有限预览。",
    ],
    video_bullets=["Codex 大更新：任务能在共享的云端环境里跨设备接着跑，新增代码审查与安全扫描，扫出的漏洞由它先在云端备好修复。"],
))

S.append(dict(
    title="Anthropic 红队评估 GLM-5.3 网络能力",
    category="要闻", nav_label="GLM-5.3", source_name="Anthropic 官方研究",
    source_url="https://www.anthropic.com/research/glm-5-3-and-the-spread-of-advanced-cyber-capabilities",
    published="2026-09-29", event_date="2026-09-29",
    event_date_evidence="Anthropic Frontier Red Team 官方研究帖 Sep 29, 2026；Simon Willison 同日引用",
    verification="official_research_post_reviewed_methodology_limits_flagged",
    bullets=[
        "Anthropic 的 Frontier Red Team 在 9月29日发布对智谱 GLM-5.3 的评估：它像自家的 Claude Mythos Preview 一样，能自主构建端到端的网络攻击利用，但发布时缺少有效防护。",
        "评估称在模拟测试里用简单手法绕过 GLM-5.3 防护的成功率从 64% 到 100%，同类攻击对受防护的 Claude 模型没有奏效；随机一百个任务的内部基准中，它 4% 的试次完成完整控制流劫持。",
        "限制是这是 Anthropic 自己的内部基准与模拟环境，不是真实攻击，也没有第三方复测；美国 NIST 下属机构 9月17日 的评估称它是迄今最具网络能力的开放权重模型，落后美国前沿约四个月。",
    ],
    video_bullets=["Anthropic 红队评估智谱 GLM-5.3 能自主写出完整攻击利用，绕过它防护的成功率最高到 100%，安全性明显低于同级 Claude 模型。"],
))

S.append(dict(
    title="OpenAI 称 ChatGPT 周活超 12 亿",
    category="要闻", nav_label="ChatGPT", source_name="IT之家",
    source_url="https://www.ithome.com/1/008/532.htm",
    published="2026-09-30T02:47:22+08:00", event_date="2026-09-29",
    event_date_evidence="OpenAI 9月29日 DevDay 公布；IT之家 9月30日（北京时间）2:47 报道",
    verification="official_figure_reported_by_media_not_independently_audited",
    bullets=[
        "OpenAI 在 9月29日的开发者日上公布，ChatGPT 每周活跃用户已经超过 12 亿，比 7 月公布的 10 亿又涨了一截；面向工作的 ChatGPT Work 与 Codex 每周用户超过 3500 万。",
        "公司称使用其产品的企业达到 250 万家，并把增长归因于生成式人工智能从个人应用走向工作场景，文档处理、数据分析和软件开发是主要用法。",
        "限制是这些数字都由 OpenAI 自己公布，没有第三方审计口径，也没有区分真人用户与自动化调用；企业端能否留住取决于集成深度，官方没有提供留存数据。",
    ],
    video_bullets=["OpenAI 说 ChatGPT 每周活跃用户已超过 12 亿，ChatGPT Work 和 Codex 周活超 3500 万，企业客户达到 250 万家。"],
))

S.append(dict(
    title="传 OpenAI 洽谈 300 亿美元新融资",
    category="行业动态", nav_label="OpenAI", source_name="TechCrunch AI",
    source_url="https://techcrunch.com/2026/09/29/openai-repotedly-in-talks-to-raise-30b-round-at-1-4t-valuation/",
    published="2026-09-29T19:52:00+00:00", event_date="2026-09-29",
    event_date_evidence="彭博社 9月29日报道，经 TechCrunch 9月29日 19:52（UTC）转述",
    verification="media_report_based_on_anonymous_sources_flagged",
    supporting_sources=[dict(name="彭博社原报道", url="https://www.bloomberg.com/news/articles/2026-09-29/openai-targets-30-billion-in-new-funding-at-1-4-trillion-value")],
    bullets=[
        "彭博社在 9月29日报道，OpenAI 正与投资人洽谈至少 300 亿美元的上市前融资，估值约 1.4 万亿美元；今年 3 月它曾以 8520 亿美元估值融到 1220 亿美元。",
        "报道称因为把重心调整到编程等方向，公司年化收入从 7 月起增长 70%，8 月达到 400 亿美元；此前这轮被认为会是上市前最后一轮，但首席执行官已排除 2026 年上市。",
        "限制是消息来自彭博社引述的知情人士，OpenAI 没有回应媒体询问，金额和估值都可能变化；公司自己把上市节奏放慢，也与近期的安全争议有关。",
    ],
    video_bullets=["OpenAI 被曝正洽谈至少 300 亿美元的新融资、估值约 1.4 万亿美元，年化收入 8 月已达 400 亿美元，公司未回应。"],
))

briefing = dict(
    date="2026-09-30",
    window_days=5,
    edition_start_date="2026-09-21",
    title="AI 日报 · 2026-09-30",
    edition_note=("本期 8 条以 OpenAI 开发者日（9月29日）为主线：GPT-6.1 Sol 模型、Dots 常驻代理、Ultrafast 速度档与 Pro 500、"
                  "Decisions API、Codex 云环境与安全扫描，另有 ChatGPT 周活 12 亿、300 亿美元融资传闻，以及 Anthropic 红队对智谱 "
                  "GLM-5.3 网络能力的官方评估。事件日期按来源官方标注记录，厂商自评与匿名信源已分别注明限制。"),
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
        first = re.split(r'[，,；;]', b)[0]
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
    if s['source_name'] not in t and s['source_name'] in vb:
        problems.append(f"口播含来源名: {t}")

print(f"stories: {len(S)}")
for s in S:
    print(f"  {s['nav_label']:<13} | 标题{len(s['title']):>2} | bullets 总{sum(len(b) for b in s['bullets']):>3}字（最长 {max(len(b) for b in s['bullets'])}）| 口播{len(s['video_bullets'][0]):>2}字 | {s['title']}")
print("自查问题:", problems or "无")

out = Path('data/briefing-2026-09-30-models.json')
out.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding='utf-8')
print("写入:", out)
