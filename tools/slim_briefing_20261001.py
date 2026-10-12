# -*- coding: utf-8 -*-
"""精简 2026-10-01 稿件要点到单页容量内。"""
import json, re
from pathlib import Path

p = Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean/data/briefing-2026-10-01-models.json')
b = json.loads(p.read_text(encoding='utf-8'))

NEW = {
 'Gemini 4 Argon': [
  "Google DeepMind 在 9月30日发布 Gemini 4 Argon，官方称是迄今最先进的模型，主打长流程软件工程、企业知识和网络安全防御，但暂未对公众开放。",
  "它单次输出上限约一百万 tokens，是此前六万四千的十五倍以上；谷歌给出的长周期代码基准 DeepSWE v1.1 得分 77.9%，高于 Claude Opus 5.5 的 74.2%。",
  "限制是分阶段开放：第一阶段只给 Fairwind 计划里的受信任防守方；成绩全部出自谷歌自己，没有第三方复测，起步价每百万输入 2 美元、输出 10 美元。",
 ],
 'DeepSeek': [
  "DeepSeek 在 9月30日开源面向华为昇腾的算子库与通信库，包括 TileLang、DeepGEMM、FlashMLA、DeepEP 等组件，与此前的 GPU 版一一对应。",
  "华为提供昇腾接口与 UBL128 超节点组网，实测互联带宽 Dispatch 375 GB/s；在 EP32 部署下，DeepSeek-V4.1-Flash 每卡吞吐可达每秒 2469 至 5102 个 token。",
  "限制是性能数字来自双方自己的离线测试，不含服务调度与框架负载均衡；这篇报道由华为供稿、量子位转载，不是独立第三方评测。",
 ],
 'Vera Rubin': [
  "CoreWeave 在 9月30日的大会上宣布 NVIDIA Vera Rubin NVL72 系统可用，并推出号称首款为 AI 代理设计的 CPU Vera。",
  "应用实验室 Cognition 是首个在生产环境跑 Vera Rubin 的客户：在真实软件工程任务上，SWE-2 推理的词元吞吐比上一代最高提升 4.8 倍。",
  "限制是这些数字来自 Cognition 与 CoreWeave 的早期测试，由 NVIDIA 官方博客发布，没有独立复测；新系统目前只面向早期访问客户。",
 ],
}

problems = []
for s in b['stories']:
    if s['nav_label'] in NEW:
        s['bullets'] = NEW[s['nav_label']]
    for bl in s['bullets']:
        first = re.split(r'[，,；;：]', bl)[0]
        if len(first) > 76:
            problems.append(f"首句 {len(first)}>76 [{s['nav_label']}]")
    total = sum(len(x) for x in s['bullets'])
    mx = max(len(x) for x in s['bullets'])
    vb = s['video_bullets'][0]
    if total > 290: problems.append(f"总长 {total} 偏大 [{s['nav_label']}]")
    if not (40 <= len(vb) <= 100): problems.append(f"口播 {len(vb)} 字 [{s['nav_label']}]")
    print(f"  {s['nav_label']:<15} 要点总{total:>3}字（最长 {mx}）| 口播{len(vb)}字")

p.write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding='utf-8')
print('自查问题:', problems or '无')
