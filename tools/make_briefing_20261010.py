# -*- coding: utf-8 -*-
"""生成 2026-10-10（第20期）AI 日报稿件。规则见 skill media/ai-daily-report references/editorial-rules.md。"""
import json, os

DATE = "2026-10-10"
EDITION_START = "2026-09-21"  # 系列起点，勿改

stories = [
    {
        "title": "字节豆包工作接入豆包 2.1 Lite，并上线创作画布",
        "category": "模型发布",
        "nav_label": "字节",
        "source_name": "雷峰网",
        "source_url": "https://www.leiphone.com/category/industrynews/J8Nj09CidhwiTl90.html",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "雷峰网 2026年10月9日 11:20《豆包工作新增画布功能，并接入豆包2.1 Lite模型》",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "字节跳动在 10 月 9 日更新豆包工作，新增轻量级模型豆包 2.1 Lite，主要面向日常问答、文档撰写、表格处理和 PPT 制作等高频办公场景。",
            "官方称该模型在响应速度与额度消耗上做了优化，图片、视频和音频理解能力较为突出，在教育、办公等多模态场景的表现有所提升，用户升级客户端后即可选用。",
            "同批上线的还有创作画布功能，把素材、设计方案与创作成果放进同一张无限画布，并接入新的图片模型 Seedream 5.0 Flash，可从理解需求一路生成图片、视频和成套设计。",
        ],
        "video_bullets": [
            "字节更新豆包工作，新增轻量的豆包 2.1 Lite 模型，主打办公问答和文档处理，速度更快也更省额度。",
        ],
        "supporting_sources": [
            {"name": "雷峰网：豆包工作新增画布功能，并接入豆包2.1 Lite模型",
             "url": "https://www.leiphone.com/category/industrynews/J8Nj09CidhwiTl90.html"},
        ],
    },
    {
        "title": "星动纪元 VPP2 世界动作模型登顶 RoboDojo 并开源",
        "category": "模型发布",
        "nav_label": "星动纪元",
        "source_name": "量子位",
        "source_url": "https://www.qbitai.com/2026/10/502125.html",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "量子位 2026年10月9日 11:52《清华具身模型登顶全球第一》；VPP2 论文与开源仓库 github.com/roboterax/video-prediction-policy-2",
        "verification": "vendor_claim_with_paper_and_open_repo",
        "bullets": [
            "星动纪元自研的世界动作模型 VPP2 登顶 RoboDojo 仿真榜单，综合平均成功率 32.26%、平均得分 39.26，两项均列第一，模型现已开源。",
            "据官方披露，GPT-6-Astra 在同一评测中平均成功率 22.48%、得分 28.97，VPP2 分别领先 9.78 个百分点和 10.29 分，在泛化、精细操作与记忆三个维度也拿下第一。",
            "团队把视频预测与动作学习分阶段训练，先把事件级预测练强再用蒸馏提速到约 0.12 秒，最后训练 0.9B 的动作专家，使真实 ALOHA 双臂机器人零样本操作平均成功率达 58.5%，高于 π0.5 的 40%。",
        ],
        "video_bullets": [
            "星动纪元的世界动作模型 VPP2 登顶 RoboDojo 榜单，平均成功率 32.26% 位列第一，在真实机器人上的零样本操作也领先，并且已经开源。",
        ],
        "supporting_sources": [
            {"name": "GitHub: roboterax/video-prediction-policy-2",
             "url": "https://github.com/roboterax/video-prediction-policy-2"},
        ],
    },
    {
        "title": "联想天禧 TianxiCode 代码智能体登顶 SWE-bench-Live",
        "category": "开发生态",
        "nav_label": "联想",
        "source_name": "量子位",
        "source_url": "https://www.qbitai.com/2026/10/502422.html",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "量子位 2026年10月9日《联想天禧自研代码智能体TianxiCode斩获SWE-bench-Live全球第一》，文中给出 71% 问题解决率与官方 Verified 认证",
        "verification": "vendor_claim_with_third_party_benchmark",
        "bullets": [
            "联想天禧 AI 自研的代码智能体框架 TianxiCode，在 10 月 9 日公布的 SWE-bench-Live（Lite 分榜）中以 71% 的问题解决率登顶全球第一，并通过官方 Verified 核验。",
            "该成绩由 TianxiCode 配合 DeepSeek-v4.1-Flash 取得，官方核验要求提交完整智能体运行轨迹，并排查是否向智能体泄露标准答案或测试用例，以确认结果可复现。",
            "TianxiCode 具备跨文件多跳检索、自驱动规划与多轮工具调用、闭环补丁生成与测试驱动自愈等能力，联想称后续会把它应用到自家 AI 硬件产品中。",
        ],
        "video_bullets": [
            "联想天禧自研的代码智能体框架 TianxiCode，配合 DeepSeek-v4.1-Flash 在 SWE-bench-Live 榜上以 71% 的解决率拿到全球第一。",
        ],
        "supporting_sources": [
            {"name": "量子位：联想天禧自研代码智能体TianxiCode斩获SWE-bench-Live全球第一",
             "url": "https://www.qbitai.com/2026/10/502422.html"},
        ],
    },
    {
        "title": "小米发通知：MiMo-V2.5 系列下线，迁移至 V2.6",
        "category": "模型发布",
        "nav_label": "小米",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/011/146.htm",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "IT之家 2026年10月9日《小米发布 MiMo-V2.5-Pro 模型下线通知，可替换为 V2.6 版本》，给出 10 月 14 日与 10 月 21 日两个时间节点",
        "verification": "official_vendor_notice_via_media",
        "bullets": [
            "小米在 10 月 9 日发布 MiMo-V2.5-Pro 与 MiMo-V2.5 的下线通知，建议开发者尽快迁移到推理能力更强、性价比更高的 MiMo V2.6 系列。",
            "替换关系为 mimo-v2.5-pro 换成 mimo-v2.6-pro、mimo-v2.5 换成 mimo-v2.6-flash，从 10 月 14 日 18:00 起旧名的请求会自动转发并按新模型计价。",
            "旧的模型名称将在 10 月 21 日 10:00 正式失效，届时继续调用会直接报错；MiMo-V2.6 系列包含 Pro 与 Flash 两个原生全模态模型，沿用了 V2.5 的 API 定价。",
        ],
        "video_bullets": [
            "小米发布通知，MiMo-V2.5 系列模型将下线，建议开发者迁移到更强的 MiMo V2.6。旧名称 10 月 21 日起彻底失效，届时调用会报错。",
        ],
        "supporting_sources": [
            {"name": "IT之家：小米 MiMo-V2.6 发布：Pro 与 Flash 双版本价格不变",
             "url": "https://www.ithome.com/1/005/496.htm"},
        ],
    },
    {
        "title": "华为 openJiuwen 开源企业级 AgentOS",
        "category": "开发生态",
        "nav_label": "华为",
        "source_name": "量子位",
        "source_url": "https://www.qbitai.com/2026/10/502106.html",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "量子位 2026年10月9日《openJiuwen发布并开源企业级AgentOS》；项目地址 github.com/openJiuwen-ai/agentos-enterprise",
        "verification": "vendor_announcement_with_open_repo",
        "bullets": [
            "由华为 2012 实验室、华为云等团队联合高校与企业共建的开源项目 openJiuwen，在 10 月 9 日发布并开源了企业级 AgentOS，把多智能体协同、自演进、算力调度与企业级安全放进统一底座。",
            "它通过蜂群协同与工作流编排支持任务拆解、角色分工和并行执行，并借助执行轨迹、用户反馈与记忆机制让智能体持续自演进，把有效经验沉淀为可复用能力。",
            "平台采用插件化架构，提供多租户隔离、安全沙箱、权限管理与故障恢复；华为在 HC2026 上还发布了基于该 AgentOS 的一体机开源加速平台，称可实现小时级私有化部署。",
        ],
        "video_bullets": [
            "华为参与共建的开源项目 openJiuwen 发布企业级 AgentOS，把多智能体协同、自演进和企业级安全放进统一底座，并已开源。",
        ],
        "supporting_sources": [
            {"name": "GitHub: openJiuwen-ai/agentos-enterprise",
             "url": "https://github.com/openJiuwen-ai/agentos-enterprise"},
        ],
    },
    {
        "title": "字节 TRAE 把写代码与出文档合并，升级全链路开发平台",
        "category": "开发生态",
        "nav_label": "字节",
        "source_name": "量子位",
        "source_url": "https://www.qbitai.com/2026/10/502426.html",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "量子位 2026年10月9日 17:19《TRAE终于把Code和Work合并了》；雷峰网 10月9日《TRAE全面升级：双端融合，打造全链路开发平台》",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "字节的 AI 编程工具 TRAE 在 10 月 9 日把原来的 TraeCode 和 TraeWork 合并成新的 TRAE，用户不必再在两个工具之间来回切换。",
            "新 TRAE 提供 Agent 模式与 IDE 模式：Agent 模式是全局工作台，可在一个窗口里把不同任务分给多个智能体并行推进，需要改细节时在右上角一键切到 IDE。",
            "文档、设计、代码和测试成果统一收进“我的产物”页并可直接分享，桌面、网页、手机三端同步，还支持和飞书、微信绑定，在群里 @TRAE 就能跨平台下任务。",
        ],
        "video_bullets": [
            "字节的 AI 编程工具 TRAE 把写代码和出文档两个工具合并成一个，用多个智能体并行推进整条开发链路，还能一键切回 IDE 改细节。",
        ],
        "supporting_sources": [
            {"name": "雷峰网：TRAE全面升级：双端融合，打造全链路开发平台",
             "url": "https://www.leiphone.com/category/industrynews/wmndjzo2jLJzOY0Z.html"},
        ],
    },
    {
        "title": "谷歌被曝内部测试 Gemini 4 新版本“Carbon”",
        "category": "模型发布",
        "nav_label": "Google",
        "source_name": "IT之家",
        "source_url": "https://www.ithome.com/1/011/162.htm",
        "published": "2026-10-10",
        "event_date": "2026-10-10",
        "event_date_evidence": "IT之家 2026年10月10日引述《商业内幕》获得的内部文档与截图，称员工测试代号 Carbon 的 Gemini 4 版本并接入内部代码平台 Jetski（谷歌拒绝置评）",
        "verification": "media_report_of_unconfirmed_internal_testing",
        "bullets": [
            "IT之家 10 月 10 日引述《商业内幕》报道，谷歌即将向公众正式发布 Gemini 4“Argon”，同时内部员工已在测试性能更强的后续版本“Carbon”。",
            "内部文档与截图显示，Carbon 很可能是 Argon 架构下的新检查点，并已接入谷歌内部代码平台 Jetski；有员工称它代码能力“堪比 Opus 5.5”，但表示仍需更深入的评测验证。",
            "也有员工反馈早期 Argon 处理部分编程任务仍显吃力，水平大体相当于 Claude Opus 5；谷歌内部还在测试 Barium、Carbon 等多款 Gemini 4 衍生模型，谷歌拒绝对此置评。",
        ],
        "video_bullets": [
            "谷歌被曝即将正式发布 Gemini 4“Argon”，内部员工已在测试性能更强的后续版本“Carbon”，据说代码能力接近 Opus 5.5，不过谷歌没有回应。",
        ],
        "supporting_sources": [
            {"name": "IT之家：谷歌 Gemini 4“Argon”模型即将发布，消息称内部测试“Carbon”新版本",
             "url": "https://www.ithome.com/1/011/162.htm"},
        ],
    },
    {
        "title": "Asana 用 GPT-6 Astra 把浏览器智能体成本降 76 倍",
        "category": "产品应用",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/asana-browser-agent",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "OpenAI 官网 2026年10月9日案例《Asana cuts model costs 76x in browser tests with GPT-6.1 Sol》",
        "verification": "official_vendor_case_study",
        "bullets": [
            "OpenAI 在 10 月 9 日公布 Asana 的案例：工程师用 Codex 里的 GPT-6 Astra 调查并优化 StackAI 浏览器智能体，最终在 GPT-6.1 Sol 上把成本降低 76 倍、速度提升 5 倍。",
            "优化前每次运行按 Model B 计约 36.21 美元，优化后降到 0.47 美元、单次约 4 分钟，做法包括把浏览历史纳入缓存、增大可保留文本量、以及攒够截图再批量删除。",
            "这项 144 次运行的对照实验由 GPT-6 Astra 自行完成，工程团队只负责定方向与复核；Asana 称按人工估计这项调查原本要 1 到 2 个月，实际约一周就完成。",
        ],
        "video_bullets": [
            "Asana 用 Codex 里的 GPT-6 Astra 优化浏览器智能体后，模型成本降低 76 倍、速度提升 5 倍。",
        ],
        "supporting_sources": [
            {"name": "OpenAI: Asana cuts model costs 76x in browser tests with GPT-6.1 Sol",
             "url": "https://openai.com/index/asana-browser-agent"},
        ],
    },
    {
        "title": "Sophos 用 OpenAI Daybreak 把威胁调查时间缩短 96%",
        "category": "产品应用",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/sophos",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "OpenAI 官网 2026年10月9日案例《Sophos cuts threat investigation time by 96% with OpenAI Daybreak》",
        "verification": "official_vendor_case_study",
        "bullets": [
            "安全厂商 Sophos 在 10 月 9 日公布的案例中，借助 OpenAI 的 Daybreak 项目把安全事件的调查时间缩短了 96%。",
            "Sophos 原来的平均响应时间约 38 分钟，用上基于 Daybreak 打造的智能体后降到约 89 秒，目前约 52% 的托管检测响应（MDR）事件可由 AI 端到端处理。",
            "这些智能体负责采集客户上下文、检测结果与威胁情报，再走“计划—执行—复核”循环生成处置建议；可能造成破坏的操作仍要人工审批，客户可选择通知、协作或授权三种模式。",
        ],
        "video_bullets": [
            "安全厂商 Sophos 用 OpenAI 的 Daybreak 打造调查智能体，把安全事件平均响应时间从约 38 分钟缩短到 89 秒，降幅 96%。",
        ],
        "supporting_sources": [
            {"name": "OpenAI: Sophos cuts threat investigation time by 96% with OpenAI Daybreak",
             "url": "https://openai.com/index/sophos"},
        ],
    },
    {
        "title": "TypeSafe AI 融资 8.7 亿美元，Jev 模型估值 75 亿",
        "category": "行业动态",
        "nav_label": "TypeSafe AI",
        "source_name": "TechCrunch",
        "source_url": "https://techcrunch.com/2026/10/09/the-maker-of-non-text-ai-model-jev-valued-at-7-5b-just-weeks-after-launch/",
        "published": "2026-10-09",
        "event_date": "2026-10-09",
        "event_date_evidence": "TechCrunch 2026年10月9日《The maker of non-text AI model Jev valued at $7.5B just weeks after launch》",
        "verification": "media_report_of_funding_round",
        "bullets": [
            "开发非文本 AI 模型 Jev 的 TypeSafe AI，在 10 月 9 日被报道以 75 亿美元估值完成 8.7 亿美元融资，由 a16z 领投，红杉与老股东 DCVC 参投。",
            "Jev 基于 Transformer 架构，但输出不是文字，而是概率或公司所称的“校准决策”，主打比大语言模型更快、更省 token，面向自动化任务而非文本或代码生成。",
            "TypeSafe AI 称已有三分之一的世界 500 强企业在使用 Jev，公司由前 OpenAI 研究员 Diogo Almeida 与 Sasha Sheng、Erik Gafni 于 2024 年共同创立。",
        ],
        "video_bullets": [
            "开发非文本模型 Jev 的 TypeSafe AI 完成 8.7 亿美元融资，估值达到 75 亿美元，由 a16z 领投，公司称已有三分之一的世界 500 强在用它的模型。",
        ],
        "supporting_sources": [
            {"name": "TechCrunch: The maker of non-text AI model Jev valued at $7.5B",
             "url": "https://techcrunch.com/2026/10/09/the-maker-of-non-text-ai-model-jev-valued-at-7-5b-just-weeks-after-launch/"},
        ],
    },
]

briefing = {
    "date": DATE,
    "window_days": 5,
    "edition_start_date": EDITION_START,
    "title": f"AI 日报 · {DATE}",
    "edition_note": (
        "本期 10 条覆盖 10 月 9 日至 10 月 10 日：模型侧有字节豆包 2.1 Lite 与创作画布、星动纪元 VPP2 登顶 RoboDojo 并开源、"
        "联想 TianxiCode 配合 DeepSeek-v4.1-Flash 登顶 SWE-bench-Live、小米 MiMo-V2.5 下线迁移 V2.6，以及谷歌被曝测试 Gemini 4 新版本 Carbon；"
        "开发与平台侧是华为 openJiuwen 开源企业级 AgentOS、字节 TRAE 双端融合；应用侧是 Asana 与 Sophos 用 OpenAI 模型大幅降本；"
        "最后是 TypeSafe AI（Jev）以 75 亿美元估值完成 8.7 亿美元融资。厂商自评成绩与自家基准均在画面要点里注明，未标注的即为第三方或官方口径。"
    ),
    "stories": stories,
}

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", f"briefing-{DATE}-models.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(briefing, f, ensure_ascii=False, indent=1)
print("written:", out, "stories:", len(stories))
# 自查
import re
for i, s in enumerate(stories, 1):
    for b in s["bullets"]:
        first = re.split(r"[，,；;]", b)[0]
        assert re.search(r"[，。；]", b), f"[{i}] bullet 缺中文标点: {b[:30]}"
        assert len(first) <= 76, f"[{i}] 首分句过长 {len(first)}: {first}"
    vb = "".join(s["video_bullets"])
    assert len(vb) <= 100, f"[{i}] 口播过长 {len(vb)}"
    assert "http" not in vb and "来源" not in vb and "…" not in vb and "..." not in vb
    assert not re.search(r"据.{0,20}(报道|消息)", vb), f"[{i}] 口播含来源表述"
    sn = s.get("source_name") or ""
    if sn and sn not in (s.get("title") or ""):
        assert sn not in vb, f"[{i}] 口播含 source_name({sn}) 但标题里没有"
print("self-check OK")
