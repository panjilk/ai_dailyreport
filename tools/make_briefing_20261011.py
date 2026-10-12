# -*- coding: utf-8 -*-
"""生成 2026-10-11（第21期）AI 日报稿件。规则见 skill media/ai-daily-report references/editorial-rules.md。"""
import json, os, re

DATE = "2026-10-11"
EDITION_START = "2026-09-21"  # 系列起点，勿改

stories = [
    {
        "title": "英伟达 Nemotron 模型 IOI 2026 超过人类最高分",
        "category": "模型发布",
        "nav_label": "NVIDIA",
        "source_name": "Hugging Face",
        "source_url": "https://huggingface.co/blog/nvidia/nemotron-ioi-and-imo-2026",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "英伟达 2026年10月7日在 Hugging Face 博客发布《One Model Family, Two Gold-Level Results: Fine-Tuning Nemotron for IOI and IMO》；IOI 论文 arXiv:2609.02849、IMO 论文 arXiv:2609.10712",
        "verification": "vendor_reported_benchmark_not_independently_verified",
        "bullets": [
            "英伟达在 10 月 7 日公布，专为竞赛编程微调的 Nemotron-3-Ultra-CC 在 IOI 2026 取得 535.4 分（满分 600），超过人类选手最高分 498.27，也高于 361.12 的金牌线。",
            "团队从 Nemotron 3 出发，用 22000 道竞赛题做监督微调，再叠加 GenCorrect 的生成、评估、修正循环；30B 总参数、3B 激活的 Nano-CC 在 IOI 2025 拿到 468 分，越过 438.3 的金牌线。",
            "同一套方法用到数学：Nemotron 3 Ultra 的 SFT 与 RL 检查点在 IMO 2026 由官方评分得 30/42 分，超过 29 分金牌线；英伟达在文中注明 IOI 成绩属非官方、无监督实测，未经独立复核。"
        ],
        "video_bullets": [
            "英伟达用 Nemotron 3 微调出的模型，在国际信息学奥赛拿到 535.4 分，首次超过人类选手最高分，用同一套方法还在国际数学奥赛拿下金牌线以上的成绩。"
        ],
        "supporting_sources": [
            {"name": "arXiv: IOI 2026 with Nemotron (2609.02849)",
             "url": "https://arxiv.org/abs/2609.02849"},
            {"name": "arXiv: IMO 2026 proof system (2609.10712)",
             "url": "https://arxiv.org/abs/2609.10712"},
        ],
    },
    {
        "title": "阶跃星辰 Step 5 Preview 登顶 OpenRouter",
        "category": "模型发布",
        "nav_label": "阶跃星辰",
        "source_name": "雷峰网",
        "source_url": "https://www.leiphone.com/category/industrynews/7iRgmb0q4JgVbmU8.html",
        "published": "2026-10-10",
        "event_date": "2026-10-10",
        "event_date_evidence": "雷峰网 2026年10月10日 11:37《阶跃 Step 5 Preview 登上 OpenRouter 全球第一，10月15日开源！》",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "阶跃星辰的旗舰基座模型 Step 5 Preview 在 10 月 10 日登上 OpenRouter Trending 榜第一、日榜全球第二，官方确认 10 月 15 日正式开源。",
            "它采用稀疏 MoE 架构，总参数量 6000 亿、每个 Token 激活约 270 亿，重点针对 AI 编程、软件工程、专业知识工作与金融等场景做了优化。",
            "在 Artificial Analysis 榜单上它的综合智能指数为 44 分，位列全球开源前三；研究员 Elvis Saravia 试用后认为能力可与 GLM-5.3、Kimi K3 相比，价格更有竞争力。"
        ],
        "video_bullets": [
            "阶跃星辰的 Step 5 Preview 登上 OpenRouter 榜首，这是 6000 亿参数的稀疏 MoE 模型，主打编程和专业知识工作，10 月 15 日就会正式开源。"
        ],
        "supporting_sources": [
            {"name": "雷峰网：阶跃 Step 5 Preview 登上 OpenRouter 全球第一",
             "url": "https://www.leiphone.com/category/industrynews/7iRgmb0q4JgVbmU8.html"},
        ],
    },
    {
        "title": "LightOn 开源 LightOnOCR-3 文档解析模型",
        "category": "模型发布",
        "nav_label": "LightOn",
        "source_name": "Hugging Face",
        "source_url": "https://huggingface.co/blog/lightonai/lightonocr-3",
        "published": "2026-10-08",
        "event_date": "2026-10-08",
        "event_date_evidence": "LightOn 2026年10月8日新闻稿《LightOn releases LightOnOCR-3》与同日 Hugging Face 博客《LightOnOCR-3: High-Performance OCR and Layout Extraction in One Model》",
        "verification": "vendor_announcement_with_open_weights",
        "bullets": [
            "法国 AI 公司 LightOn 在 10 月 8 日发布并开源 LightOnOCR-3，一次性给出 0.8B、1B、4B 三个尺寸，沿用 Apache 2.0 许可，可自由商用。",
            "新版在一个模型里同时做文字识别与版面理解：把提示词设为 grounding，就能输出带标签的文本框、图片描述，并把图表数据抽成表格。",
            "官方公布的成绩中，4B 版在 olmOCR-Bench 得 86.3 分、在 ParseBench 五类综合上以 75.1 分排第一，0.8B 版在 ParseBench 得 74.6 分位列第二。"
        ],
        "video_bullets": [
            "法国公司 LightOn 开源了文档解析模型 LightOnOCR-3，一次放出三个尺寸，能同时做文字识别和版面分析，还能把图表里的数据抽成表格。"
        ],
        "supporting_sources": [
            {"name": "LightOn：LightOnOCR-3 产品与研究页",
             "url": "https://www.lighton.ai/research/lightonocr-3"},
        ],
    },
    {
        "title": "阿联酋 TII 发布 Falcon-ASR 语音模型",
        "category": "模型发布",
        "nav_label": "TII",
        "source_name": "TII",
        "source_url": "https://huggingface.co/blog/tiiuae/falcon-asr",
        "published": "2026-10-07",
        "event_date": "2026-10-07",
        "event_date_evidence": "阿布扎比技术创新研究院（TII）2026年10月7日在 Hugging Face 博客发布《Introducing Falcon ASR》",
        "verification": "vendor_reported_benchmark_on_public_leaderboard",
        "bullets": [
            "阿布扎比技术创新研究院（TII）在 10 月 7 日发布 Falcon-ASR，这是一个 1.6B 参数的语音识别模型，重点针对阿拉伯语与阿联酋方言。",
            "在 ELM 研究中心维护的阿拉伯语 ASR 榜单上，它在六个测试集的平均词错率为 20.92%，比该榜当时最好的 23.17% 低 2.25 个百分点。",
            "同一份权重还能识别英语、法语、西班牙语和葡萄牙语，无需指定语种；TII 自测英语七个测试集平均词错率 5.74%，并支持词级时间戳。"
        ],
        "video_bullets": [
            "阿联酋的技术创新研究院发布 1.6B 的 Falcon-ASR 语音模型，主攻阿拉伯语和阿联酋方言，在公开榜单上把平均词错率降到 20.92%，同一个模型还能听懂五种语言。"
        ],
        "supporting_sources": [
            {"name": "Hugging Face：Falcon-ASR 模型与演示",
             "url": "https://huggingface.co/spaces/tiiuae/falcon-asr-demo"},
        ],
    },
    {
        "title": "Oracle 13 万人用上 ChatGPT 与 Codex",
        "category": "产品应用",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/oracle",
        "published": "2026-10-08",
        "event_date": "2026-10-08",
        "event_date_evidence": "OpenAI 官网 2026年10月8日客户案例《How Oracle turns days of work into minutes with ChatGPT and Codex》",
        "verification": "official_vendor_case_study",
        "bullets": [
            "OpenAI 在 10 月 8 日公布甲骨文的案例：这家公司已有 13 万名 ChatGPT 活跃用户和 9.5 万多名 Codex 活跃用户，覆盖招聘、工程与 IT 运营。",
            "招聘团队用 ChatGPT Work 搭出人才市场情报工具，把原本要 2 到 4 天完成的岗位调研压缩到 15 至 20 分钟，官方给出的降幅是 98%。",
            "Oracle Applications Lab 用 Codex 把公司对象与规则做成一套本体，业务人员用自然语言提问就能自动生成 SQL 并返回报告，不必再找人代查。"
        ],
        "video_bullets": [
            "甲骨文已有 13 万人在用 ChatGPT、9.5 万多人用 Codex，招聘团队把原本要几天的岗位调研压缩到十几分钟，业务提问也能直接生成报表。"
        ],
        "supporting_sources": [
            {"name": "OpenAI: How Oracle turns days of work into minutes",
             "url": "https://openai.com/index/oracle"},
        ],
    },
    {
        "title": "腾讯元器平台宣布 11 月 9 日停止服务",
        "category": "行业动态",
        "nav_label": "腾讯",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/011/530.htm",
        "published": "2026-10-10",
        "event_date": "2026-10-08",
        "event_date_evidence": "腾讯元器 2026年10月8日发布《关于元器平台停止服务通知》，IT之家 10月10日 22:42 报道《腾讯元器将于 11 月 9 日停止服务》",
        "verification": "official_vendor_notice_via_media",
        "bullets": [
            "腾讯元器在 10 月 8 日发布停服通知，因业务调整，这个一站式智能体创造与分发平台将于 2026 年 11 月 9 日正式停止服务。",
            "从 10 月 29 日起平台停止创建新智能体与 API key 分发；停服后应用访问、数据读写、API 调用和控制台全部关闭，发布到公众号、微信客服等渠道的智能体也不再响应。",
            "用户可在停服前随时导出智能体配置、工作流与对话记录；官方把数据保留到 2027 年 1 月 9 日，之后除法规要求留存的记录外将删除全部用户数据。"
        ],
        "video_bullets": [
            "腾讯元器平台宣布 11 月 9 日停止服务，已创建的智能体届时不再可用，官方建议用户尽快导出数据或迁移业务。"
        ],
        "supporting_sources": [
            {"name": "IT之家：腾讯元器将于 11 月 9 日停止服务",
             "url": "https://www.ithome.com/1/011/530.htm"},
        ],
    },
    {
        "title": "阿里云百炼下线 DeepSeek、Kimi、GLM 等模型",
        "category": "行业动态",
        "nav_label": "阿里",
        "source_name": "阿里云",
        "source_url": "https://www.alibabacloud.com/help/en/model-studio/model-depreciation",
        "published": "2026-10-10",
        "event_date": "2026-10-10",
        "event_date_evidence": "阿里云百炼（Model Studio）模型下线公告页标注「Scheduled for deprecation on October 10, 2026」，六份公告统一在北京时间 10 月 10 日 00:00 生效",
        "verification": "official_cloud_service_notice",
        "bullets": [
            "10 月 10 日起，阿里云百炼平台上的一批第三方便携快照模型正式停止服务，DeepSeek-R1、V3、V3.1、V3.2，智谱 GLM-4.6、GLM-4.7，月之暗面 Kimi K2 与 MiniMax-M2.1 都在名单里。",
            "受影响的多为快照版本，官方给每一项的推荐替代都是同一个：qwen3.7-plus，256K 以内输入每百万 Token 0.4 元、输出 1.6 元。",
            "这些模型并未被各自的厂商停用，开源权重与自己家的 API 仍在，变的是阿里云不再托管它们；同期下线的还有 qwen3-asr-flash 与 qwen3-tts-flash 两个语音端点。"
        ],
        "video_bullets": [
            "阿里云百炼从 10 月 10 日起下线 DeepSeek、Kimi、GLM、MiniMax 等第三方模型，统一建议迁移到自家的 qwen3.7-plus，官方说法是资源优化。"
        ],
        "supporting_sources": [
            {"name": "Alibaba Cloud：Model Studio 模型下线公告",
             "url": "https://www.alibabacloud.com/zh/notice/detail?id=2009"},
        ],
    },
    {
        "title": "Manus 完成超 5 亿美元融资并重启北京招聘",
        "category": "行业动态",
        "nav_label": "Manus",
        "source_name": "36氪",
        "source_url": "https://m.36kr.com/p/4016873172144008",
        "published": "2026-10-08",
        "event_date": "2026-10-08",
        "event_date_evidence": "Manus 母公司北京蝴蝶效应 2026年10月8日官宣；36氪 10月8日《官宣5亿美元新一轮融资，Manus开启下一程》，另见联合早报 10月8日报道",
        "verification": "company_announcement_via_media",
        "bullets": [
            "通用智能体公司 Manus 的母公司北京蝴蝶效应在 10 月 8 日宣布完成超过 5 亿美元新一轮融资，由博裕投资与 IDG 资本领投，老股东腾讯、红杉中国、真格基金继续跟投。",
            "多家媒体报道其投后估值约 40 亿美元；公司同日放出 17 个岗位，覆盖产品、研发、运营与增长，工作地点全部在北京。",
            "Manus 在此前把团队迁往新加坡、海外总部仍留在新加坡，这次融资与招聘被外界看作它重新加码国内市场、与国产智能体产品正面竞争的信号。"
        ],
        "video_bullets": [
            "通用智能体公司 Manus 完成超过 5 亿美元融资，由博裕和 IDG 领投，腾讯等老股东跟投，估值约 40 亿美元，同时在北京放出 17 个岗位。"
        ],
        "supporting_sources": [
            {"name": "联合早报：Manus经历收购风波后融资5亿美元",
             "url": "https://www.zaobao.com.sg/finance/china/story20261008-9806401"},
        ],
    },
]

briefing = {
    "date": DATE,
    "window_days": 5,
    "edition_start_date": EDITION_START,
    "title": f"AI 日报 · {DATE}",
    "edition_note": (
        "本期 8 条覆盖 10 月 7 日至 10 月 10 日：模型侧有英伟达 Nemotron 微调体系在 IOI 2026 超过人类最高分、"
        "阶跃星辰 Step 5 Preview 登顶 OpenRouter 并将于 10 月 15 日开源、LightOn 开源 LightOnOCR-3 文档解析模型、"
        "阿联酋 TII 发布 1.6B 的 Falcon-ASR 阿拉伯语语音模型；应用侧是甲骨文 13 万人用上 ChatGPT 与 Codex；"
        "行业侧是腾讯元器 11 月 9 日停服、阿里云百炼 10 月 10 日下线 DeepSeek/Kimi/GLM 等第三方模型、"
        "以及 Manus 完成超 5 亿美元融资并重启北京招聘。厂商自评成绩已在画面要点里注明口径，未标注的即为第三方或官方基准。"
    ),
    "stories": stories,
}

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", f"briefing-{DATE}-models.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(briefing, f, ensure_ascii=False, indent=1)
print("written:", out, "stories:", len(stories))
# 自查
for i, s in enumerate(stories, 1):
    assert len(s["title"]) <= 40, f"[{i}] 标题过长 {len(s['title'])}: {s['title']}"
    assert not re.search(r"[…]|\.\.\.", s["title"]), f"[{i}] 标题含省略号"
    for b in s["bullets"]:
        first = re.split(r"[，,；;]", b)[0]
        assert re.search(r"[，。；]", b), f"[{i}] bullet 缺中文标点: {b[:30]}"
        assert len(first) <= 76, f"[{i}] 首分句过长 {len(first)}: {first}"
    vb = "".join(s["video_bullets"])
    assert 40 <= len(vb) <= 100, f"[{i}] 口播长度 {len(vb)}: {vb}"
    assert "http" not in vb and "来源" not in vb and "…" not in vb and "..." not in vb
    assert not re.search(r"据.{0,20}(报道|消息)", vb), f"[{i}] 口播含来源表述"
    sn = s.get("source_name") or ""
    if sn and sn not in (s.get("title") or ""):
        assert sn not in vb, f"[{i}] 口播含 source_name({sn}) 但标题里没有"
print("self-check OK")
