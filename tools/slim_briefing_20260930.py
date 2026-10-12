# -*- coding: utf-8 -*-
"""精简 2026-09-30 稿件要点到单页容量内。"""
import json, re
from pathlib import Path

p = Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean/data/briefing-2026-09-30-models.json')
b = json.loads(p.read_text(encoding='utf-8'))

NEW = {
 'GPT-6.1 Sol': [
  "OpenAI 在 9月29日发布 GPT-6.1 Sol，是 GPT-6 Sol 的升级版：在智能体编程、电脑操作和专业工作上接近旗舰 GPT-6 Astra，价格只有它的五分之一。",
  "短上下文的标准档每百万 tokens 输入 2 美元、输出 10 美元，缓存输入 0.1 美元、比上一代低一半；批量与弹性档再打五折，另有加价优先处理的快速档。",
  "限制是评测数据都来自 OpenAI 自己：低推理强度下事实错误率从 11.4% 降到 7.7%，官方称各档与 Astra 差距在 1.9% 以内，尚无第三方复测。",
 ],
 'Ultrafast': [
  "OpenAI 在 9月29日推出 Ultrafast 速度档：它不是新模型，而是优先算力档，官方称在 Codex 里词元生成最高快八倍、API 快六倍，约每秒三百个词元。",
  "代价在价格：API 端按标准价的六倍计费，Astra 相当于每百万 tokens 输入 60 美元、输出 300 美元；同时上线每月 500 美元的 Pro 500 订阅。",
  "限制是快的是生成速度，不等于整个任务快八倍，官方也说明了上线期速率限制；新的 Pro 200 额度下调，GPT-6 Pro 消息从每周 200 条减到 100 条。",
 ],
 'GLM-5.3': [
  "Anthropic 红队在 9月29日评估智谱 GLM-5.3：它能像 Claude Mythos Preview 一样自主构建端到端攻击利用，但发布时缺少有效防护。",
  "评估称模拟测试里用简单手法绕过它防护的成功率从 64% 到 100%，同类攻击对受防护的 Claude 无效；随机一百个任务中它 4% 的试次完成完整控制流劫持。",
  "限制是这来自 Anthropic 自己的内部基准与模拟环境，不是真实攻击，也没第三方复测；NIST 下属机构 9月17日 称它是迄今最具网络能力的开放权重模型。",
 ],
}

problems = []
for s in b['stories']:
    if s['nav_label'] in NEW:
        s['bullets'] = NEW[s['nav_label']]
    for bl in s['bullets']:
        first = re.split(r'[，,；;]', bl)[0]
        if len(first) > 76:
            problems.append(f"首句 {len(first)}>76 [{s['nav_label']}]")
    total = sum(len(x) for x in s['bullets'])
    vb = s['video_bullets'][0]
    if not (40 <= len(vb) <= 100):
        problems.append(f"口播 {len(vb)} 字 [{s['nav_label']}]")
    if total > 290:
        problems.append(f"总长 {total} 偏大 [{s['nav_label']}]")
    print(f"  {s['nav_label']:<13} bullets 总{total:>3}字（最长 {max(len(x) for x in s['bullets'])}）| 口播{len(vb)}字")

p.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding='utf-8')
print('自查问题:', problems or '无')
