#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-10-08 AI 日报稿件（Hermes 手写，逐条核对官方原文）。

窗口：北京时间 2026-10-04 ~ 2026-10-08，本期以 10月7日（含美西时间当日发布的事件）为主。
期号：2026-10-08 - 2026-09-21 + 1 = 第18期。
"""
import json
import re
from datetime import date
from pathlib import Path

REPORT_DATE = "2026-10-08"
EDITION_START = "2026-09-21"
OUT = Path(__file__).resolve().parent.parent / "data" / f"briefing-{REPORT_DATE}-models.json"
CLAUSE_MAX = 76

STORIES = [
    {
        "title": "Anthropic 发布最便宜的 Claude Haiku 5.5",
        "category": "模型发布",
        "nav_label": "Anthropic",
        "source_name": "Anthropic",
        "source_url": "https://www.anthropic.com/claude-haiku-5-5",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "Anthropic 官方发布页《Introducing Claude Haiku 5.5》(anthropic.com/claude-haiku-5-5) 与官方账号 10月7日（当地时间）公布；平台文档 platform.claude.com 给出 1M 上下文与 128K 输出上限；IT之家 10月8日 6:26（北京时间）报道同一发布",
        "verification": "official_announcement_with_vendor_benchmarks_not_independently_verified",
        "bullets": [
            "Anthropic 在 10月7日发布 Claude Haiku 5.5，称它是自家最快、最便宜、能力最强的小型模型，上下文窗口从上一代的 20 万 token 提升到 100 万，单次最长输出 12.8 万 token。",
            "价格是这次最大的变化：请求不超过 10 万 token 时，每百万输入 0.10 美元、输出 0.50 美元，比 Haiku 4.5 低约 90%；超过 10 万 token 后为 0.50 和 2.50 美元，官方估算整体运行成本平均低约 75%。",
            "它是首个可以调节思考力度的 Haiku 模型，官方给 OSWorld 2.1 电脑操作 72.4%、Terminal-Bench 4.0 编程 39.2% 的自评成绩，并把它定位成 Opus 5.5、Sonnet 5.5 写代码时的子智能体。",
        ],
        "video_bullets": [
            "Anthropic 发布 Claude Haiku 5.5，号称又快又便宜，最长能读一百万 token，价格不到上一代的十分之一。它还支持调节思考力度，可以给更大的模型打下手。"
        ],
        "supporting_sources": [
            {"name": "Anthropic Docs: What's new in Claude Haiku 5.5",
             "url": "https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5"},
            {"name": "IT之家：Anthropic 最快、最便宜模型 Claude Haiku 5.5 登场",
             "url": "https://www.ithome.com/1/010/333.htm"},
        ],
    },
    {
        "title": "OpenAI 让 ChatGPT 全员用上 GPT-6 和智能界面",
        "category": "模型发布",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/gpt-6-for-everyone",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "OpenAI 官方文章《GPT-6 and Intelligent UI for everyone》(openai.com/index/gpt-6-for-everyone)，官方 RSS 时间戳 Wed, 07 Oct 2026 00:00:00 GMT；IT之家 10月8日 6:10（北京时间）据其 X 推文报道同一发布",
        "verification": "official_announcement",
        "bullets": [
            "OpenAI 在 10月7日宣布，GPT-6 系列模型开放给所有 ChatGPT 用户：Astra、Sol、Luna 此前只供 ChatGPT Work 与 Codex 使用，普通用户长期停留在 GPT-5.6 系列。",
            "同步上线的智能界面（Intelligent UI）会根据问题自己组合文字、图像和交互元素来回答，回复里可以有图表、可点击按钮和表单，不再是纯文字段落。",
            "官方举的例子是用互动可视化的方式教用户打麻将，并称这些视觉效果会随用户的学习、尝试和发现做出反应；OpenAI 同时公布 ChatGPT 全球周活跃用户已超过 12 亿。",
        ],
        "video_bullets": [
            "OpenAI 把 GPT-6 系列开放给所有 ChatGPT 用户，周活跃用户已经超过十二亿。新版还带来智能界面，回答里能直接放图表、按钮和表单，比如用互动的方式教你打麻将。"
        ],
        "supporting_sources": [
            {"name": "IT之家：周活超 12 亿用户，OpenAI ChatGPT 升级 GPT-6 模型",
             "url": "https://www.ithome.com/1/010/327.htm"},
            {"name": "TechCrunch: ChatGPT is getting a lot more visual, with the launch of a new interface",
             "url": "https://techcrunch.com/2026/10/07/chatgpt-is-getting-a-lot-more-visual-with-the-launch-of-a-new-interface/"},
        ],
    },
    {
        "title": "微软把 MAI Code 1.1 Flash 引入 Win11",
        "category": "模型发布",
        "nav_label": "Microsoft",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/010/308.htm",
        "published": "2026-10-08",
        "event_date": "2026-10-07",
        "event_date_evidence": "微软在太平洋时间 10月7日上午 10 点（北京时间 10月8日凌晨 1 点）旧金山 Windows 与 Surface 发布会上宣布；IT之家 10月8日 1:29（北京时间）报道该发布会；同日 GitHub Copilot 本地推理报道给出 1370 亿总参数、680 亿活跃参数",
        "verification": "vendor_announcement_at_event_reported_by_media",
        "bullets": [
            "微软在 10月7日的发布会上宣布，把自研代码模型 MAI Code 1.1 Flash 引入 Windows 11：总参数 1370 亿、每次激活 680 亿，3-bit 量化后体积缩小 80%，上下文窗口 256K。",
            "它已经接进 GitHub Copilot 与 VS Code，用于日常编码、仓库问答、重构和工具调用；官方称比 6 月版本在 Copilot CLI 的 Terminal-Bench 2.1 上提升约 22%，.NET 任务提升约 15%，输出速度提升约 25%。",
            "新版补上了看图写代码的能力，可以直接读截图、架构图和 UI 草图；在 Surface Laptop Ultra 上实测，提示从 2K 到 256K token 时解码吞吐在每秒 40 到 63 个词元之间。",
        ],
        "video_bullets": [
            "微软发布 MAI Code 1.1 Flash，总参数一千三百七十亿、每次激活六百八十亿，三比特量化后体积缩小八成。它将接进 GitHub Copilot 和 VS Code。"
        ],
        "supporting_sources": [
            {"name": "IT之家：GitHub Copilot 不再纯云端 AI 模型，本地推理吞吐量最高每秒 63 词元",
             "url": "https://www.ithome.com/1/010/330.htm"},
        ],
    },
    {
        "title": "Liquid AI 开源边缘决策模型 d1-3B",
        "category": "模型发布",
        "nav_label": "Liquid AI",
        "source_name": "Liquid AI",
        "source_url": "https://huggingface.co/blog/LiquidAI/open-d1",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "Liquid AI 官方博客《Multimodal open d1 decision models for the edge》10月7日发布（huggingface.co/blog/LiquidAI/open-d1），同步在 Hugging Face 开源 d1-3b 与 d1-omni-600M 权重",
        "verification": "official_announcement_with_vendor_benchmarks",
        "bullets": [
            "Liquid AI 在 10月7日开源两个面向边缘设备的决策模型 d1-3B 与 d1-omni-600M：决策模型不逐字生成，而是一次前向计算直接给出答案，官方称 d1-3B 在 Decision Index 0.2.1 上拿到 48.57 分，是 100 亿参数以下的最好成绩。",
            "它超过所有 40 亿和 90 亿级别模型，也超过亚马逊 350 亿参数的 Decider 模型；d1-3B 支持文字和图像输入，实验性的 d1-omni-600M 支持文字配图像或文字配音频。",
            "速度上，d1-3B 在英伟达 Jetson AGX Thor 上回答一个问题只要 16 毫秒，AGX Orin 上 26 毫秒，Orin Nano 上 50 毫秒；官方称这些数字来自与英伟达的联合测试，没有第三方复现。",
        ],
        "video_bullets": [
            "Liquid AI 开源两个能在本地设备跑的决策模型，最大的 d1-3B 只有三十亿参数，不做逐字生成、一次前向就给出答案。它在英伟达边缘芯片上回答一个问题只要十六毫秒。"
        ],
        "supporting_sources": [
            {"name": "Hugging Face: LiquidAI/d1-3b 模型页",
             "url": "https://huggingface.co/LiquidAI/d1-3b"},
        ],
    },
    {
        "title": "英伟达发布 RTX Spark 与桌面超算 DGX Station",
        "category": "产品应用",
        "nav_label": "NVIDIA",
        "source_name": "NVIDIA",
        "source_url": "https://blogs.nvidia.com/blog/local-ai-rtx-spark-microsoft-windows-event/",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "NVIDIA 官方博客《NVIDIA, Microsoft Kick Off a New Beginning for Windows PCs With RTX Spark and AI Agents》标注 October 7, 2026（微软旧金山发布会当天）；IT之家 10月8日 1:52 / 1:56（北京时间）报道同一发布会",
        "verification": "official_announcement_with_vendor_specs",
        "bullets": [
            "英伟达在 10月7日的微软发布会上公布 RTX Spark 芯片，把 Blackwell RTX GPU 与最高 20 核 Grace CPU 放进笔记本和小型主机，最高 128GB 统一内存、约 1 PFLOPS 的 FP4 算力。",
            "RTX Spark 笔记本当天开始预售、10月16日发货；微软同步公布搭载它的 Surface Laptop Ultra 起售价 2599 美元，本月开订。",
            "同场发布 DGX Station for Windows 桌面超级计算机，用 GB300 Grace Blackwell Ultra 芯片、最高 748GB 统一内存和 20 PFLOPS 算力，能在本地跑约一万亿参数模型，第四季度上市、最高功耗 1600 瓦。",
        ],
        "video_bullets": [
            "英伟达发布 RTX Spark 笔记本芯片和 DGX Station 桌面超算，后者有最高七百四十八GB内存，能在本地跑一万亿参数的模型。搭载它的笔记本当天开始预售。"
        ],
        "supporting_sources": [
            {"name": "IT之家：英伟达发布 DGX Station for Windows",
             "url": "https://www.ithome.com/1/010/313.htm"},
        ],
    },
    {
        "title": "GitHub Copilot 本月底支持本地模型推理",
        "category": "开发生态",
        "nav_label": "GitHub",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/010/330.htm",
        "published": "2026-10-08",
        "event_date": "2026-10-07",
        "event_date_evidence": "微软在太平洋时间 10月7日上午 10 点（北京时间 10月8日凌晨 1 点）旧金山发布会上宣布；IT之家 10月8日 6:17（北京时间）报道该发布会内容",
        "verification": "vendor_announcement_at_event_reported_by_media",
        "bullets": [
            "微软在 10月7日的发布会上宣布，GitHub Copilot 将在本月底前支持本地模型推理，开发者可以在云端模型和设备端模型之间自动或手动切换；目前它仍然依赖云端托管模型，由协调器按性能、成本和准确性路由请求。",
            "Copilot 会提供自动编排和强制本地两种模式，用户可以在 Copilot CLI、Copilot 应用与 VS Code 里设置偏好；本地模型可以通过 Windows ML 选择 MAI Code 1.1 Flash，也可以连接 OpenAI 兼容的本地端点。",
            "官方在 Surface Laptop Ultra 上实测，提示长度从 2K 到 256K token 时，本地解码吞吐在每秒 40 到 63 个词元之间；所用模型为混合专家架构，靠量化与推测解码压低响应时间和内存占用。",
        ],
        "video_bullets": [
            "微软宣布 GitHub Copilot 本月底支持本地模型推理，开发者可以在云端和本机模型之间自动切换，也能强制用设备端模型。官方在自家笔记本上实测，本地解码速度最高每秒六十三个词元。"
        ],
        "supporting_sources": [],
    },
    {
        "title": "微软发布 MXC SDK 给智能体受控执行环境",
        "category": "开发生态",
        "nav_label": "Microsoft",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/010/307.htm",
        "published": "2026-10-08",
        "event_date": "2026-10-07",
        "event_date_evidence": "IT之家 10月8日 1:24（北京时间）转引 The Verge 对微软 10月7日（太平洋时间上午 10 点）旧金山 Windows 与 Surface 发布会的报道",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "微软在 10月7日的 Windows 与 Surface 发布会上重点介绍 MXC（Microsoft Execution Containers）SDK，它给 AI 智能体提供相对独立的执行环境，让智能体在受控范围内执行代码、调用工具，尽量减少接触用户敏感数据。",
            "微软把 MXC 称为 Windows AI 战略的重要组成，与 Agent 365、Microsoft IQ 一起构成智能体的安全与治理底座，让 Windows 上的智能体不只是回答问题，而能本地执行更复杂的操作。",
            "微软暂未公布 MXC 的完整技术细节、开放范围和上线时间；官方说法是这些能力直接做进 Windows，让智能体可以被安全地运行、观测和治理。",
        ],
        "video_bullets": [
            "微软介绍了给智能体用的 MXC 开发套件，它让 AI 在独立的沙盒里执行代码、调用工具，尽量少碰用户的敏感数据。技术细节和上线时间还没公布。"
        ],
        "supporting_sources": [
            {"name": "The Verge: Microsoft's MXC SDK coverage",
             "url": "https://www.theverge.com/"},
        ],
    },
    {
        "title": "Meta 的 Muse 智能体将以原生应用登陆 Windows",
        "category": "产品应用",
        "nav_label": "Meta",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/010/310.htm",
        "published": "2026-10-08",
        "event_date": "2026-10-07",
        "event_date_evidence": "微软在 10月7日（太平洋时间）旧金山发布会上由 Windows 与设备部门负责人帕万·达武鲁里宣布；IT之家 10月8日 1:45（北京时间）报道；同日 IT之家报道 Meta 推出 iPad 版 Muse（10月7日）",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "微软在 10月7日的发布会上表示，Meta 的 Muse 智能体将以原生应用形式登陆 Windows，并集成微软的 MXC SDK；同日 Meta 为 Muse 推出 iPad 版，新增 Canva、Dropbox、Figma、QuickBooks、GitHub、Klaviyo、Zoom 等连接器。",
            "微软还展示了多款第三方智能体工具：Perplexity 的便携电脑工具能在端侧执行复杂任务、不消耗云积分；Windows 将新增智能体入门指南，OpenClaw 也会推出原生 Windows 网关。",
            "Muse 最早在 9 月登陆 iPhone，随后推出 Mac 版，过去几周一直排在美国 App Store 免费 iPhone 应用下载榜首位。",
        ],
        "video_bullets": [
            "Meta 的 Muse 智能体将以原生应用登陆 Windows，并接入微软的智能体沙盒；它同时推出 iPad 版，新增 Figma、Zoom、GitHub 等连接器。"
        ],
        "supporting_sources": [
            {"name": "IT之家：适配大屏，Meta 推出 iPad 版 Muse AI 智能体",
             "url": "https://www.ithome.com/1/010/295.htm"},
        ],
    },
    {
        "title": "谷歌开放 SynthID 检测网站",
        "category": "技术洞察",
        "nav_label": "Google",
        "source_name": "Google",
        "source_url": "https://blog.google/innovation-and-ai/models-and-research/google-deepmind/synth-id-ai-content/",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "谷歌官方博客《Google expands SynthID Detector for AI content》与 synthid.com 全球开放同日；The Verge 发布于 Oct 7, 2026 2:00 PM UTC、Engadget 10月7日报道全球开放；TechCrunch 10月7日同题报道",
        "verification": "official_announcement_with_media_confirmation",
        "bullets": [
            "谷歌在 10月7日把 SynthID Detector 开放给所有人：登录 synthid.com 就能上传图片、视频或音频，检查里面有没有 SynthID 隐式水印，此前这个工具只提供给记者、媒体从业者和研究人员试用。",
            "它支持 JPG、PNG、WEBP、HEIC、TIFF、GIF 等图像格式，MP4、MOV、WEBM 视频，以及 WAV、MP3、OGG、FLAC 等音频；谷歌称检测能力已经做进 Gemini 应用和 Chrome，目前每天约有 100 万次内容核验请求。",
            "除谷歌自家的 Nano Banana、Veo、Lyria 生成的内容，OpenAI、英伟达和 Kakao 也支持 SynthID 水印，苹果即将加入；不过各家水印检测并不完美，此前有测试发现它们识别不出自己模型生成的裁剪图。",
        ],
        "video_bullets": [
            "谷歌把 SynthID 检测网站开放给所有人，上传图片、视频或音频就能查里面有没有 AI 隐式水印。现在谷歌自家模型、OpenAI 和英伟达生成的内容都在检测范围内，每天已有约一百万次核验请求。"
        ],
        "supporting_sources": [
            {"name": "TechCrunch: Google's new SynthID website can identify AI-generated media",
             "url": "https://techcrunch.com/2026/10/07/googles-new-synthid-website-can-identify-ai-generated-media/"},
        ],
    },
    {
        "title": "Nous Research 完成 B 轮，估值 15 亿美元",
        "category": "行业动态",
        "nav_label": "Nous Research",
        "source_name": "TechCrunch",
        "source_url": "https://techcrunch.com/2026/10/07/nous-research-confirms-it-hit-1-5b-valuation-launches-ai-agents-for-business-users/",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "TechCrunch 10月7日报道《Nous Research confirms it hit $1.5B Valuation, launches AI agents for business users》，引用官方融资说明 nousresearch.com/a-note-on-our-fundraise 与《华尔街日报》收入数据",
        "verification": "media_report_of_vendor_fundraise",
        "bullets": [
            "开发开源智能体 Hermes 的 Nous Research 在 10月7日确认完成 9000 万美元 B 轮融资，估值 15 亿美元，由 Robot Ventures 领投，英伟达、Union Square Ventures、Menlo Ventures、三星等参投，累计融资约 1.58 亿美元。",
            "官方估计开源的 Hermes 智能体已被克隆超过 2400 万次，约占全球 AI token 用量的 2.5%；新资金将用于推出面向企业的 Hermes for Businesses，让公司部署能处理多步工作流程、同时保持数据私有的定制智能体。",
            "《华尔街日报》报道称，这家成立三年的公司 9 月中旬的年化收入约 3600 万美元，并预计在 2026 年底前突破 1 亿美元。",
        ],
        "video_bullets": [
            "开发开源智能体 Hermes 的 Nous Research 完成九千万美元融资，估值十五亿美元，英伟达和三星都参与投资。官方称开源的 Hermes 被克隆超过两千四百万次，接下来要推出企业版。"
        ],
        "supporting_sources": [
            {"name": "Nous Research: A note on our fundraise",
             "url": "https://nousresearch.com/a-note-on-our-fundraise"},
        ],
    },
]


def main() -> None:
    problems = []
    for s in STORIES:
        if re.search(r'研究团队|研究人员|作者|海外观点|AI 行业', s["title"]) or \
           re.search(r'研究团队|研究人员|作者', s["nav_label"]):
            problems.append(f"[{s['nav_label']}] 标题/底栏出现禁用词")
        if "…" in s["title"] or "..." in s["title"]:
            problems.append(f"[{s['nav_label']}] 标题含省略号")
        if len(s["title"]) > 40:
            problems.append(f"[{s['nav_label']}] 标题 {len(s['title'])} 字 >40")
        total = 0
        for b in s["bullets"]:
            total += len(b)
            if not re.search(r'[，。；：]', b):
                problems.append(f"[{s['nav_label']}] 要点无中文标点")
            fc = re.split(r'[，,；;]', b)[0]
            if len(fc) > CLAUSE_MAX:
                problems.append(f"[{s['nav_label']}] 首分句 {len(fc)} 字: {fc}")
            if len(b) > 290:
                problems.append(f"[{s['nav_label']}] 要点 {len(b)} 字 >290")
        if total > 360:
            problems.append(f"[{s['nav_label']}] 要点合计 {total} 字偏长")
        if not 2 <= len(s["bullets"]) <= 3:
            problems.append(f"[{s['nav_label']}] 要点条数 {len(s['bullets'])}")
        vb = "".join(s["video_bullets"])
        if len(vb) > 100:
            problems.append(f"[{s['nav_label']}] 口播 {len(vb)} 字 >100")
        if len(vb) < 40:
            problems.append(f"[{s['nav_label']}] 口播 {len(vb)} 字 <40")
        if re.search(r'http|来源|据.{0,20}(报道|消息)|…|\.\.\.', vb):
            problems.append(f"[{s['nav_label']}] 口播命中禁令")
        if s["source_name"] in vb and s["source_name"] not in s["title"]:
            problems.append(f"[{s['nav_label']}] 口播出现 source_name 且不在标题")

    if problems:
        print("!! 校验失败:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    y, m, d = map(int, REPORT_DATE.split("-"))
    sy, sm, sd = map(int, EDITION_START.split("-"))
    edition = (date(y, m, d) - date(sy, sm, sd)).days + 1

    note = (
        f"本期 {len(STORIES)} 条覆盖 10月7日（美西时间当日发布）：Anthropic 最便宜的小型模型 Claude Haiku 5.5 居首，"
        "随后是 OpenAI 把 GPT-6 系列与智能界面开放给所有 ChatGPT 用户、微软 MAI Code 1.1 Flash 引入 Win11 与 Copilot、"
        "Liquid AI 开源的边缘决策模型 d1-3B；产品与开发工具部分是英伟达 RTX Spark 与 DGX Station、GitHub Copilot 本地推理、"
        "微软 MXC SDK、Meta Muse 登陆 Windows 和谷歌 SynthID 检测网站；最后是 Nous Research 的 B 轮融资。"
        "厂商自评成绩与自建基准均在画面要点里注明。"
    )

    data = {
        "date": REPORT_DATE,
        "window_days": 5,
        "edition_start_date": EDITION_START,
        "title": f"AI 日报 · {REPORT_DATE}",
        "edition_note": note,
        "stories": STORIES,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"期号 = {edition}")
    print(f"已写出: {OUT}  条数={len(STORIES)}")


if __name__ == "__main__":
    main()
