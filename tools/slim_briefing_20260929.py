# -*- coding: utf-8 -*-
"""精简 2026-09-29 稿件要点，控制在单页容量内（复刻昨天渲染成功的长度）。"""
import json, re
from pathlib import Path

p = Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean/data/briefing-2026-09-29-models.json')
b = json.loads(p.read_text(encoding='utf-8'))

NEW = {
 'Anthropic': [
  "Anthropic 在 9月28日发布 Sonnet 5.5，官方称输出比上代快三成以上，单价每百万 tokens 输入 2 美元、输出 10 美元，只有 Opus 5.5 的一半。",
  "官方评测中它在代理编程测试 Terminal-Bench 4.0 拿到 70.6%，高于 Opus 5.5 的 66.4%；因网络安全能力接近 Opus 5，它首次被施加同级网络防护。",
  "限制来自独立机构：最高档思考下每任务写约 19.3 万 tokens，单任务约 7.6 美元，比 Sonnet 5 贵约五成，省钱只在中低档位；Haiku 更新要等几周。",
 ],
 'MiniMax': [
  "MiniMax 在 9月27日上线文本模型 M3.1-Flash-Preview，先接入自家编程工具 MiniMax Code，定位日常开发，从快速修 bug 到实现完整功能。",
  "同时开启限时活动：9月28日到10月7日按北京时间签到可拿双倍免费额度，新老用户都能参加，上线时所有 Token Plan 配额被重置。",
  "限制是它仍是 Preview，官方只给出快和稳这类宣传性描述，没有公布参数量、定价或评测分数。",
 ],
 'ElevenLabs': [
  "ElevenLabs 在 9月28日发布基于新架构的语音合成模型 Eleven v4 和低延迟版 v4 Turbo，两款都支持九十多种语言，用十秒音频就能做即时音色克隆。",
  "官方称 v4 最有表现力，在 Artificial Analysis 排名第一、盲测中约 75% 听众更偏好它；Turbo 的中位首次语音延迟约 150 毫秒。",
  "限制是排名与盲测由厂商或其委托机构完成，没有第三方复现；它做的是语音合成，不是通用大模型，官方也未给出独立压测数据。",
 ],
 'NVIDIA': [
  "NVIDIA 在 9月28日发布 Open Agent Safety Platform，由开源运行时 OpenShell 与硬件监控层 Sentry 组成，前者限制代理能访问的文件、凭证和网络。",
  "Sentry 跑在 BlueField-4 数据处理单元上从外部监控，公司称能毫秒级隔离越界代理，还称若早用于模型评测，Hugging Face 被入侵本可避免。",
  "限制是这些效果都是 NVIDIA 的说法，没有公开基准或独立红队复测；参与机构超 100 家，含 Anthropic 与微软，OpenAI 不在名单里。",
 ],
 'Shopify': [
  "Shopify 在 9月28日把 WebMCP 支持扩展到结账环节，包括 Shop Pay，浏览器里的 AI 代理由此能在买家授权后读取结账页、改写信息并提交订单。",
  "新增 get_checkout、update_checkout 和 complete_checkout 三个工具，代理可改地址与配送方式后下单，不靠截图或抓页面。",
  "限制是每一步都要买家授权，平台没开放无授权自动付款；Amazon 等商家正在反向屏蔽代理下单，规则并不统一。",
 ],
 'Google': [
  "Google 在 9月28日确认停用 Gemini 的自定义助手功能 Gems，并按应用内提示在 11月17日把它们统一改造成 skills。",
  "官方说明用户自建和预置的 Gems 都会自动迁移，不用自己动手，11月17日之前仍可正常使用；Gems 是 2024 年推出、用来免去重复描述任务的功能。",
  "限制是改用 skills 后要在任务线程输入斜杠再挑技能，操作更像工程工具而不是聊天；官方未说明 skills 能否像 Gems 那样分享。",
 ],
 'AMD': [
  "AMD 在 9月28日宣布以 82 亿美元收购世界模型公司 World Labs，创始人李飞飞将出任 AMD 执行副总裁兼首席科学家。",
  "World Labs 成立于 2024 年，首个产品 Marble 用于生成娱乐体验，也能造给机器人训练用的仿真环境；两家去年已做推理优化与训练合作。",
  "限制是交易预计年底前完成并需监管审批；世界模型定义模糊、商业化路径不明，此举主要是补 AMD 对标 NVIDIA 生态的短板。",
 ],
}

problems = []
for s in b['stories']:
    key = s['nav_label']
    if key in NEW:
        s['bullets'] = NEW[key]
    t = s['title']
    if len(t) > 40:
        problems.append(f'标题过长({len(t)}): {t}')
    for bl in s['bullets']:
        first = re.split(r'[，,；;]', bl)[0]
        if len(first) > 76:
            problems.append(f'首句 {len(first)}>76: {key}')
    total = sum(len(x) for x in s['bullets'])
    vb = s['video_bullets'][0]
    if re.search(r'https?://|来源|…|\.\.\.', vb) or not (40 <= len(vb) <= 100):
        problems.append(f'口播问题({len(vb)}): {key}')
    print(f"  {key:<11} bullets 总{total:>3}字（单条最长 {max(len(x) for x in s['bullets'])}）| 口播{len(vb)}字")

p.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding='utf-8')
print('自查问题:', problems or '无')
print('已更新:', p)
