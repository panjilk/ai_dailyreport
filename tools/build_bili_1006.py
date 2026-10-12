#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-10-06 期的 B站简介 / 时间轴评论 / 来源评论。"""
import json
from pathlib import Path

D = Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean/outputs/2026-10-06_070432_798336')
b = json.loads((D / 'briefing.json').read_text(encoding='utf-8'))
tl = json.loads((D / 'timeline.json').read_text(encoding='utf-8'))

stories = b['stories']
print('briefing.json story order:')
for i, s in enumerate(stories, 1):
    print(f'  {i}. {s["nav_label"]} | {s["title"]}')

ch_start = {}
for seg in tl['segments']:
    c = seg.get('chapter')
    if c and c >= 1 and seg.get('text', '').strip() and c not in ch_start:
        ch_start[c] = seg['start']
print('chapter starts:', {k: round(v, 1) for k, v in sorted(ch_start.items())})


def mmss(x):
    x = int(x)
    return f'{x // 60}:{x % 60:02d}'


lines_tl = ['⏱ 本期时间轴（第16期）']
for i, s in enumerate(stories, 1):
    t = mmss(ch_start.get(i, 0))
    lines_tl.append(f'{t} {s["title"]}｜{s["nav_label"]}')
lines_tl.append('')
lines_tl.append('（时间轴对应视频内每条切换的时刻）')
tl_text = '\n'.join(lines_tl)

lines_src = ['📚 本期来源（第16期）']
for i, s in enumerate(stories, 1):
    lines_src.append(f'{i} {s["title"]}')
    lines_src.append('  · ' + s["source_url"].replace('https://', '').replace('http://', '').replace('www.', ''))
    for ss in s.get('supporting_sources', []) or []:
        lines_src.append('  · ' + ss["url"].replace('https://', '').replace('http://', '').replace('www.', ''))
src_text = '\n'.join(lines_src)

overview = '；'.join(f'{s["title"]}' for s in stories)
desc = (
    '10.6 AI 日报 第16期｜本期 7 条：' + overview +
    '。完整时间轴与来源见评论区。'
)

(D.parent / 'desc_1006.txt').write_text(desc, encoding='utf-8')
Path('/home/ubuntu/bili_desc_1006.txt').write_text(desc, encoding='utf-8')
Path('/home/ubuntu/bili_timeline_1006.txt').write_text(tl_text, encoding='utf-8')
Path('/home/ubuntu/bili_sources_1006.txt').write_text(src_text, encoding='utf-8')

print('\n--- desc', len(desc), '字 ---')
print(desc)
print('\n--- timeline', len(tl_text), '字 ---')
print(tl_text)
print('\n--- sources', len(src_text), '字 ---')
print(src_text)
