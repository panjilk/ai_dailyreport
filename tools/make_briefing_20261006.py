#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-10-06 AI 日报稿件（Hermes 手写，逐条核对原文）。

窗口：北京时间 2026-10-02 ~ 2026-10-06 事件。
期号：2026-10-06 - 2026-09-21 + 1 = 第16期。
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "briefing-2026-10-06-models.json"

STORIES = [
    {
        "title": "Reflection 发布 501B 开源权重模型 Beam",
        "category": "模型发布",
        "nav_label": "Reflection",
        "source_name": "Reflection",
        "source_url": "https://reflection.ai/blog/introducing-beam",
        "published": "2026-10-05",
        "event_date": "2026-10-05",
        "event_date_evidence": "Reflection 官方博客《Introducing Beam》标注 October 5, 2026；TechCrunch 同日 10月5日 12:33 太平洋时间报道",
        "verification": "official_announcement_with_vendor_benchmarks_not_independently_verified",
        "bullets": [
            "美国初创公司 Reflection 在 10月5日发布首个开源权重模型 Beam，采用稀疏混合专家架构，总参数 5010 亿、每次只激活 230 亿，主打编程、推理和智能体任务。",
            "官方称 Beam 用 23.8 万亿个 token 预训练，支持 100 万 token 上下文；它用 1.05 万块英伟达 GB300 做了四周高算力强化学习，产生超过 1 亿次 rollout。",
            "官方称 Beam 在编程和智能体任务上追平 GLM-5.2、逼近 Qwen3.8-Max，推理算力却省三到四倍；性能仍是厂商自测，权重、技术报告和模型卡要到本月晚些时候才公布。",
        ],
        "video_bullets": [
            "美国初创公司 Reflection 发布首个开源权重模型 Beam，总参数五千亿、每次只激活两百三十亿，主打编程和智能体任务。官方称它追平国产开源模型，推理算力却省三到四倍，权重本月晚些时候才放出。"
        ],
        "supporting_sources": [
            {"name": "TechCrunch：Reflection debuts Beam, an open-weight AI model to rival Chinese models at lower compute cost",
             "url": "https://techcrunch.com/2026/10/05/reflection-debuts-beam-a-open-weight-ai-model-to-rival-chinese-models-at-lower-compute-cost/"},
        ],
    },
    {
        "title": "OpenAI 给欧盟文本输出加隐形水印",
        "category": "要闻",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/eu-text-provenance",
        "published": "2026-10-05",
        "event_date": "2026-10-05",
        "event_date_evidence": "OpenAI 官方博客《Our approach to EU text provenance rules》标注 October 5, 2026；IT之家 10月5日 15:58 报道",
        "verification": "official_announcement_with_vendor_evaluations",
        "bullets": [
            "OpenAI 在 10月5日公布应对欧盟《人工智能法案》的文本水印方案，未来几周会在欧盟的 ChatGPT 和 Codex 输出里嵌入隐形水印，API 客户从当天起可自愿开启。",
            "水印技术名叫 textGrain，通过调整模型的选词加入一层统计信号；官方实测在 1% 误报率下，200 个 token 的段落检出率约 80%，400 个 token 约 95%。",
            "编辑会明显削弱水印：替换 10% 的词语后检出率从约 92% 降到 66%，替换 25% 只剩 17%；因此检测器初期只开放给审核通过的机构和研究者，水印也不能证明作者身份或内容真假。",
        ],
        "video_bullets": [
            "OpenAI 宣布在欧盟给 ChatGPT 和 Codex 的文本输出加隐形水印，用统计信号标记模型的选词。实测替换十分之一词语，检出率就从九成掉到六成多，所以检测器暂时只开放给审核过的机构。"
        ],
        "supporting_sources": [
            {"name": "IT之家：OpenAI 将在欧盟为 ChatGPT 和 Codex 文本输出添加隐形水印",
             "url": "https://www.ithome.com/1/009/903.htm"},
        ],
    },
    {
        "title": "OpenAI 在 ChatGPT 图片生成里测试视觉广告",
        "category": "产品应用",
        "nav_label": "OpenAI",
        "source_name": "OpenAI",
        "source_url": "https://openai.com/index/new-chatgpt-ads-format-and-measurement",
        "published": "2026-10-05",
        "event_date": "2026-10-05",
        "event_date_evidence": "OpenAI 官方博客《Building advertising for the way people use AI》标注 October 5, 2026；IT之家 10月5日 15:01 报道",
        "verification": "official_announcement",
        "bullets": [
            "OpenAI 在 10月5日宣布在 ChatGPT 中推出新的图片广告形式，先在图片生成过程中测试，广告会明确标注、且与正在生成的图片分开，不会影响模型给出的答案。",
            "官方称 ChatGPT 每周覆盖 12 亿人，是全球最大的原生 AI 消费平台；这项测试本月晚些时候在美国启动，首批只面向一小批广告主。",
            "OpenAI 同时扩充广告衡量工具，接入 Hightouch、LiveRamp 等数据伙伴和 AppsFlyer、Adjust 等归因平台，并与 DoubleVerify 和 Integral Ad Science 试点品牌适配度评估。",
        ],
        "video_bullets": [
            "OpenAI 开始在 ChatGPT 的图片生成里测试新广告，广告会明确标注，也不会影响模型给出的答案。官方说 ChatGPT 每周覆盖十二亿人，测试本月晚些时候在美国的一批广告主里启动。"
        ],
        "supporting_sources": [
            {"name": "IT之家：OpenAI 将在 ChatGPT 中推出全新图片广告形式，不会影响生成结果",
             "url": "https://www.ithome.com/1/009/901.htm"},
        ],
    },
    {
        "title": "Instinct 把 AI 智能体带进群聊",
        "category": "产品应用",
        "nav_label": "Instinct",
        "source_name": "TechCrunch",
        "source_url": "https://techcrunch.com/2026/10/05/instinct-brings-its-ai-agent-to-group-chats-even-for-friends-without-an-account/",
        "published": "2026-10-05T18:54:00+00:00",
        "event_date": "2026-10-05",
        "event_date_evidence": "TechCrunch 2026年10月5日 11:54 太平洋时间报道，称 Instinct 当日（周一）宣布开放群聊；创始人 Noah Shinn 同日发帖确认",
        "verification": "media_report_of_vendor_launch",
        "bullets": [
            "估值 100 亿美元的 AI 智能体公司 Instinct 在 10月5日宣布开放群聊功能，用户能把它加进和朋友的聊天里，用来规划旅行、抢演出票、组织拼车等。",
            "即使好友没有注册 Instinct，也能参与这些群聊；个人账号与群聊相互隔离，个人智能体要共享信息或代为操作前，必须先获得用户授权。",
            "据报道，Instinct 最新一轮融资 10 亿美元、估值 100 亿美元，正与 Meta 的智能体 Muse 等对手竞争，后者暂未提供群聊能力。",
        ],
        "video_bullets": [
            "估值一百亿美元的 AI 智能体 Instinct 开放群聊，把它拉进朋友群就能一起规划旅行、抢票、组织拼车，好友没注册也能用。个人智能体要共享信息前，还得先拿到用户授权。"
        ],
    },
    {
        "title": "HackerRank 的 AI 面试官 Chakra 正式开放",
        "category": "产品应用",
        "nav_label": "HackerRank",
        "source_name": "TechCrunch",
        "source_url": "https://techcrunch.com/2026/10/05/hackerranks-ai-interviewer-offers-a-glimpse-into-what-job-interviews-could-become/",
        "published": "2026-10-05T16:43:00+00:00",
        "event_date": "2026-10-05",
        "event_date_evidence": "TechCrunch 2026年10月5日 9:43 太平洋时间报道，HackerRank 同日（周一）宣布 Chakra 结束约六个月 beta、正式开放",
        "verification": "media_report_of_vendor_launch",
        "bullets": [
            "招聘平台 HackerRank 在 10月5日把 AI 面试官 Chakra 正式开放给客户，结束约六个月的测试；测试期间它已完成超过 50 万场面试，Snowflake、Capgemini 等公司参与试用。",
            "面试更像真实工作：候选人拿到一个真实代码仓库任务，在带 AI 助手的画布上完成，Chakra 会边看边追问为什么选这个方案、换一个约束会怎么改。",
            "除答案对错，它还要评估批判性思维和判断力，以及所谓的 AI 素养：候选人怎么向 AI 描述问题、判断输出，并把它推向解决方案。",
        ],
        "video_bullets": [
            "招聘平台 HackerRank 把 AI 面试官正式开放，测试期已经跑完五十多万场面试。它会边看边追问，除了答案，还看你怎么把问题描述给 AI、又怎么判断它给出的结果。"
        ],
    },
    {
        "title": "TikTok 上线 AI 购物助手与一键结算",
        "category": "产品应用",
        "nav_label": "TikTok",
        "source_name": "TechCrunch",
        "source_url": "https://techcrunch.com/2026/10/05/tiktok-rolls-out-an-ai-shopping-assistant-and-one-click-checkout/",
        "published": "2026-10-05T18:29:00+00:00",
        "event_date": "2026-10-05",
        "event_date_evidence": "TechCrunch 2026年10月5日 11:29 太平洋时间报道，TikTok 同日（周一）发布公告",
        "verification": "media_report_of_vendor_announcement",
        "bullets": [
            "TikTok 在 10月5日推出 AI 购物助手和 App 内一键结算，助手是能记住用户偏好的对话式智能体，会回答商品详情、物流、尺码和库存问题，并协助完成下单。",
            "一键结算让用户直接在推荐信息流里向品牌下单，无需跳出 App；功能与 Salesforce、Shopify、Stripe 等电商和支付平台合作实现。",
            "报道称 TikTok 想把用户的购物问答留在站内，不必转向 ChatGPT 这类外部工具；市场机构估算其 2025 年美国电商销售额约 158 亿美元，占美国社交电商约 18%。",
        ],
        "video_bullets": [
            "TikTok 推出 AI 购物助手和一键结算，助手能记住你的偏好，回答尺码、库存和物流问题，还能直接在推荐流里下单。平台想把购物问答留在自己站内，不必转向外部的聊天机器人。"
        ],
    },
    {
        "title": "英伟达展示 AI 补上乳腺癌诊疗缺口",
        "category": "行业动态",
        "nav_label": "NVIDIA",
        "source_name": "NVIDIA",
        "source_url": "https://blogs.nvidia.com/blog/ai-breast-cancer-startups/",
        "published": "2026-10-05",
        "event_date": "2026-10-05",
        "event_date_evidence": "NVIDIA 官方博客 2026年10月5日发布（作者 Chelsea Sumner）",
        "verification": "vendor_blog_with_startup_disclosed_metrics",
        "bullets": [
            "英伟达在 10月5日介绍 Inception 创业计划里的一批医疗 AI 公司，它们用 AI 覆盖乳腺癌从影像筛查、风险评估到治疗方案的全流程。",
            "初创公司 iSono Health 的 ATUSA 是获 FDA 许可的可穿戴三维超声系统，约两分钟就能扫完一侧乳房，而传统手持超声最多要 45 分钟；公司称其敏感度比手持二维超声高 28%。",
            "报道指出，美国每年要做约 4000 万次乳腺 X 光检查，未来十年放射科医生缺口预计达数万人，诊断后的基因检测又常要等上数周，这些正是创业公司想压缩的时间。",
        ],
        "video_bullets": [
            "英伟达介绍了一批用 AI 改善乳腺癌诊疗的创业公司，从两分钟扫完一侧乳房的自动超声，到更快给出方案的基因检测。美国每年要做约四千万次乳腺检查，放射科医生缺口却在扩大。"
        ],
    },
]

EDITION_START = "2026-09-21"
REPORT_DATE = "2026-10-06"
TITLE_MAX = 40
CLAUSE_MAX = 76


def first_clause(text):
    text = re.sub(r'\s+([，。！？；：])', r'\1', str(text)).strip()
    return re.split(r'[，,；;]', text)[0]


def main():
    problems = []
    for s in STORIES:
        if len(s["title"]) > TITLE_MAX:
            problems.append(f"标题过长 {len(s['title'])}: {s['title']}")
        for b in s["bullets"]:
            fc = first_clause(b)
            if len(fc) > CLAUSE_MAX:
                problems.append(f"[{s['nav_label']}] 首分句 {len(fc)} 字: {fc}")
            if not re.search(r'[，。；：]', b):
                problems.append(f"[{s['nav_label']}] 要点无中文标点")
        vb = "".join(s["video_bullets"])
        if len(vb) > 100:
            problems.append(f"[{s['nav_label']}] 口播 {len(vb)} 字 >100")
        if re.search(r'http|来源|据.{0,20}(报道|消息)|…|\.\.\.', vb):
            problems.append(f"[{s['nav_label']}] 口播命中禁令")
        if s["source_name"] in vb and s["source_name"] not in s["title"]:
            problems.append(f"[{s['nav_label']}] 口播出现 source_name 且不在标题")

    if problems:
        print("!! 校验失败:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)

    from datetime import date
    y, m, d = map(int, REPORT_DATE.split("-"))
    sy, sm, sd = map(int, EDITION_START.split("-"))
    edition = (date(y, m, d) - date(sy, sm, sd)).days + 1

    note = (
        f"本期 {len(STORIES)} 条覆盖 10月5日：Reflection 发布 501B 开源权重模型 Beam 居首，"
        "随后是 OpenAI 欧盟文本水印与 ChatGPT 图片广告、Instinct 群聊智能体、HackerRank AI 面试官 Chakra、"
        "TikTok AI 购物助手，最后是英伟达展示的乳腺癌诊疗 AI。"
        "厂商自评与自建基准的数据均在画面要点里注明。"
        "（Hinton 等 22 人关于智能爆炸的论文事件日期为 9月28日，已超出本期窗口，未收录。）"
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
