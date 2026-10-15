# -*- coding: utf-8 -*-
"""生成 2026-10-12 的 v3 稿件：口播从 49-60 字扩写到约 85 字（用户 2026-10-12 新规则）。

- 只使用 v2 稿件里已核实的画面要点事实（数字/日期/限制全部沿用，不新增未核实内容）。
- 自检：每条 75-95 计音字；不含 http/来源/据…报道/省略号；不含 source_name 原字符串（除非已在 title 里）。
"""
import json
import re
from pathlib import Path

ROOT = Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean')
src = json.loads((ROOT / 'data/briefing-final.json').read_text(encoding='utf-8'))

NARRATIONS = [
    'GPT-6.1 Sol 把 Codex 和 ChatGPT Work 的默认上下文从 27.2 万提到 50 万 token，减少长任务压缩；改的是默认值不是上限，用户仍可自行调整，最大仍保持 100 万。',
    'OpenAI 从 10 月 8 日起给 ChatGPT 付费版推送 GPT-6 和可交互界面，回答里能放对比图、示意图和计算器，思考时先给部分答案；免费与 Go 稍后扩展，只动 Chat。',
    'Claude Haiku 5.5 面向摘要、分类这类高频任务，官方估算平均成本比 4.5 低约 75%，但按输入长度分档：不超 10 万 token 时每百万输入 0.1 美元、输出 0.5 美元，同批 Sonnet 缓存读价减半。',
    '通义千问发布 Qwen-Image-2.1-Turbo，沿用 70 亿参数架构，把出图和改图压到八步去噪，支持 2K 生成和自然语言修图；权重已开放，但用 Qwen Research 许可。',
    'OpenAI 开始在 API、Codex 和 ChatGPT Work 推送 Sol Ultrafast，输出速度最高到标准版八倍；官方强调这是输出速度，应用端只面向 Pro 500 等计划。',
    '阿里千问 10 月 12 日发布 QwenGyre，用 Partial Scoring 给不完整轨迹打分，超时但部分完成也拿到反馈；在 NL2RepoBench 上训练 48 步，通过率从 52.5% 升到 58.5%。',
    '小米 MiMo 旧模型 10 月 14 日 18 点起，mimo-v2.5 系列请求自动转到 v2.6 并按新模型计价，10 月 21 日 10 点旧名称失效、调用报错，默认输出上限从 32768 提到 131072。',
    'Gemini API 把 gemini-3.7-flash 的请求自动转到 3.8 Flash、3.5 Flash 转到 3.6 Flash，开发者要改名并回归测试；10 月 23 日还停用旧版深度研究智能体。',
    'Google Cloud 推出面向企业的 Gemini 智能体，能连接邮件、文档和业务系统并调用子智能体；长任务在电脑关闭后也能在云端继续跑，企业可设权限和费用上限，金融与法律版还在预览。',
    'OpenAI 的 Tibo 在 10 月 11 日问 Pro 用户：要两倍周额度还是保持不设五小时限制；投票是保留现状更多，他说这与自己预期不同，但这只是征询，周额度并没正式翻倍。',
]


def hz(s):
    return len(re.findall(r'[\u4e00-\u9fff0-9A-Za-z]', s))


stories = src['stories']
assert len(stories) == len(NARRATIONS) == 10

problems = []
for i, (story, text) in enumerate(zip(stories, NARRATIONS), 1):
    n = hz(text)
    flag = '' if 75 <= n <= 95 else '  ❌ 超范围'
    print(f'{i:>2} {story["nav_label"]:<16} {n:>3}计音字 {len(text):>3}字符{flag}')
    if not 75 <= n <= 95:
        problems.append(f'第{i}条字数 {n}')
    if len(text) > 140:
        problems.append(f'第{i}条字符数 {len(text)} 超渲染上限 140')
    if re.search(r'https?://|来源|据.{0,20}(?:报道|消息)|…', text):
        problems.append(f'第{i}条命中口播禁词')
    sn = story['source_name']
    if sn in text and sn not in story['title']:
        problems.append(f'第{i}条口播含 source_name「{sn}」')

print('\n平均', round(sum(hz(t) for t in NARRATIONS) / 10, 1), '计音字；合计',
      sum(hz(t) for t in NARRATIONS), '字')
if problems:
    print('\n❌ 自检未通过：')
    for p in problems:
        print('  -', p)
    raise SystemExit(1)

for story, text in zip(stories, NARRATIONS):
    story['video_bullets'] = [text]

out = ROOT / 'data/briefing-2026-10-12-models-v3.json'
out.write_text(json.dumps(src, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

check = json.loads(out.read_text(encoding='utf-8'))
assert len(check['stories']) == 10
assert all(s['video_bullets'] == [t] for s, t in zip(check['stories'], NARRATIONS))
print('\n✅ 自检通过，已写入', out)
print('口播合计', sum(hz(t) for t in NARRATIONS) + 39, '计音字 → 预估成片约',
      round((sum(hz(t) for t in NARRATIONS) + 39) * 0.2119), '秒')
