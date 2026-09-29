"""One-shot AI daily report; never installs or registers a scheduler."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from html import escape
import json
import os
from pathlib import Path
import sys

from .collect import collect
from .recency import enforce_recency
from .render import CATEGORIES, prepare_briefing, render, validate_briefing, window_label

ROOT = Path(__file__).resolve().parent.parent
SHANGHAI = timezone(timedelta(hours=8))
MIN_VIDEO_STORIES = 5


def require_minimum_video_stories(briefing):
    count = len(briefing['stories'])
    if count < MIN_VIDEO_STORIES:
        raise ValueError(
            f'本期只有 {count} 条合格新闻，至少需要 {MIN_VIDEO_STORIES} 条才生成视频；'
            '请补充窗口内有明确事件和可靠来源的新闻，不使用旧闻或空泛内容凑数。'
        )


def export_text(briefing, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'briefing.json').write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding='utf-8')
    md = [f"# {briefing['date']} AI 日报", '', window_label(briefing), '', briefing.get('edition_note', ''), '']
    script = [f"{briefing['date']} AI 日报", window_label(briefing), '']
    for i, story in enumerate(briefing['stories'], 1):
        md += [f"## {i:02} · {story['category']}｜{story['title']}", '',
               f"原文发布日期：{story['published']}", '', *['- ' + x for x in story['bullets']], '',
               f"来源：[{story['source_name']}]({story['source_url']})", '',
               '**口播**', '', story['narration'], '']
        script += [f"{i:02} {story['title']}", story['narration'], '']
        if story.get('event_date'):
            md += [f"模型事件日期：{story['event_date']}", '']
        if story.get('event_date_evidence'):
            md += ['日期证据（原文）：' + story['event_date_evidence'], '']
        for source in story.get('supporting_sources', []):
            md += [f"补充证据：[{source['name']}]({source['url']})", '']
    if briefing.get('collection_errors'):
        md += ['## 采集记录', '', *['- ' + x for x in briefing['collection_errors']], '']
    if briefing.get('collection_stats'):
        labels = {'feed_entries': '读取条目', 'off_topic': '主题不符', 'source_failures': '来源失败',
                  'invalid_metadata': '时间或链接无效', 'outside_window': '报道时间超窗', 'duplicates': '重复条目',
                  'eligible_candidates': '候选总数', 'article_requests': '正文请求', 'fetch_failures': '正文请求失败',
                  'date_rejected': '事件日期不合格', 'content_rejected': '正文不合格', 'summary_rejected': '摘要不合格',
                  'selected': '最终收录', 'article_request_budget': '正文请求上限',
                  'source_cap_skipped': '来源优先上限暂缓', 'unexamined_candidates': '未检查候选', 'budget_exhausted': '预算耗尽'}
        md += ['## 筛选统计', '', *[f'- {labels.get(k, k)}：{v}' for k, v in briefing['collection_stats'].items()], '']
    if briefing.get('excluded_stories'):
        md += ['## 导入稿件筛选', '', *[f'- {x["title"]}：{x["reason"]}' for x in briefing['excluded_stories']], '']
    (output / 'report.md').write_text('\n'.join(md), encoding='utf-8')
    (output / 'script.txt').write_text('\n'.join(script), encoding='utf-8')


def write_preview(briefing, output):
    playable = (output / 'daily.mp4').is_file()
    timeline_path = output / 'timeline.json'
    manifest = json.loads(timeline_path.read_text('utf-8')) if playable and timeline_path.exists() else {}
    cards = []
    for i, story in enumerate(briefing['stories'], 1):
        bullets = ''.join(f'<li>{escape(x)}</li>' for x in story['bullets'])
        evidence_links = ''.join(f' · <a href="{escape(x["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(x["name"])} ↗</a>' for x in story.get('supporting_sources', []))
        cards.append(f'''<article><small>{i:02} / {escape(story['category'])}</small>
        <h2>{escape(story['title'])}</h2><ul>{bullets}</ul>
        <footer>{escape(story['published'][:10])} · <a href="{escape(story['source_url'], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(story['source_name'])} ↗</a>{evidence_links}</footer></article>''')
    player = ''
    if playable:
        chapters = ''.join(f'<button data-time="{float(c["start"]):.3f}">{escape(c["title"])}</button>' for c in manifest.get('chapters', []))
        duration = int(manifest.get('duration_seconds', 0))
        player = f'''<section class="player"><video id="video" controls preload="metadata" poster="cover.png" src="daily.mp4"></video>
        <div class="bar"><span>1080p · 中文配音 · {duration//60:02}:{duration%60:02}</span>
        <a href="daily.mp4" download>下载视频 ↓</a><a href="subtitles.srt" download>字幕 SRT ↓</a></div>
        <nav aria-label="视频章节">{chapters}</nav></section>'''
    else:
        player = '<p class="notice">文字采集已完成，尚未生成视频。</p>'
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 日报</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f5f3ed;color:#252f32;font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:1280px;margin:auto;padding:36px 28px 64px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #d7dbd1;padding-bottom:20px}
.brand{font-weight:800;letter-spacing:2px}.brand b{color:#bb6244}a{color:#a34f35;text-underline-offset:4px}h1{font-size:clamp(32px,5vw,58px);line-height:1.2;letter-spacing:-1px;margin:32px 0 18px}p{color:#68716b}.meta{margin-bottom:28px}
.player{background:#fff;border:1px solid #e4e6dc;border-radius:20px;overflow:hidden;margin:30px 0}video{display:block;width:100%;aspect-ratio:16/9;background:#eee}.bar{display:flex;flex-wrap:wrap;gap:22px;padding:18px 24px;border-top:1px solid #eee}.bar span{margin-right:auto;color:#69716b}
nav{display:flex;gap:8px;padding:0 22px 20px;overflow-x:auto}button{cursor:pointer;white-space:nowrap;font:inherit;font-size:13px;border:1px solid #dfe3d8;border-radius:8px;padding:8px 12px;background:#f8f8f2;color:#444}button:hover{background:#f1ded4}button:focus-visible{outline:3px solid #bb6244}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{background:#fff;border-radius:18px;padding:28px;border:1px solid #e6e8df}small{color:#bb6244;font-weight:700}h2{font-size:23px;line-height:1.5;margin:12px 0}ul{padding-left:22px;color:#4f5854}li+li{margin-top:12px}footer{font-size:13px;color:#757e77;border-top:1px solid #edf0e8;padding-top:18px;margin-top:24px}.note{font-size:14px;padding:18px 0}.notice{padding:24px;background:white;border-radius:14px}
@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:22px 16px}header{gap:12px;font-size:13px}article{padding:22px}}
</style><main>'''
    page += f'''<header><div class="brand"><b>＋</b> AI DAILY / 人工智能日报</div><span>{escape(briefing['date'])}</span></header>
<h1>AI 日报 · 资讯精选</h1><p class="meta">{escape(window_label(briefing))} · {len(briefing['stories'])} 条资讯 · <a href="report.md" download>文字日报 ↓</a> · <a href="script.txt" download>口播稿 ↓</a></p>{player}
<p class="note">{escape(briefing.get('edition_note', ''))}</p><section class="grid">{''.join(cards)}</section>
<footer>本地生成 · 新闻内容请以链接原文为准 · {escape(manifest.get('speech_engine', ''))}</footer></main>
<script>document.querySelectorAll('[data-time]').forEach(b=>b.addEventListener('click',()=>{{const v=document.getElementById('video');v.currentTime=Number(b.dataset.time);v.play().catch(()=>{{}})}}));</script></html>'''
    (output / 'index.html').write_text(page, encoding='utf-8')


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='一键采集 AI 新闻，生成中文配音日报视频。')
    parser.add_argument('--input', type=Path, help='使用已准备的 briefing JSON，跳过联网采集')
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    parser.add_argument('--hours', type=int, default=120, help='最多回看120小时，且绝不早于北京时间最近5天的首日零点')
    parser.add_argument('--limit', type=int, default=10, help='最多收录条数，默认10，允许5至12')
    parser.add_argument('--output', type=Path, help='输出目录，默认按运行时间新建')
    parser.add_argument('--collect-only', action='store_true', help='仅采集文字，不制作视频')
    parser.add_argument('--tts', choices=['auto', 'edge', 'sapi'], default='auto')
    parser.add_argument('--voice', help='联网语音，默认温和的 zh-CN-XiaoxiaoNeural')
    parser.add_argument('--rate', type=int, help='语速百分比，默认+10（约1.1倍）；支持-10至60')
    parser.add_argument('--pitch', type=int, help='音高调整，默认-8Hz；支持-20至20')
    parser.add_argument('--open', action='store_true', help='完成后打开本地预览页')
    args = parser.parse_args(argv)
    if not MIN_VIDEO_STORIES <= args.limit <= 12 or not 1 <= args.hours <= 120:
        parser.error('--limit 必须在5至12之间，--hours 必须在1至120之间。')
    if args.rate is not None and not -10 <= args.rate <= 60:
        parser.error('--rate 必须在-10至60之间。')
    if args.pitch is not None and not -20 <= args.pitch <= 20:
        parser.error('--pitch 必须在-20至20之间。')
    try:
        now = datetime.now(SHANGHAI)
        config = json.loads(args.config.read_text(encoding='utf-8-sig'))
        if args.input:
            print('正在读取已准备的新闻稿……', flush=True)
            briefing = json.loads(args.input.read_text(encoding='utf-8-sig'))
        else:
            print(f'正在采集最近 {args.hours} 小时的 AI 新闻……', flush=True)
            briefing = collect(config, now, args.hours, args.limit)
        briefing.setdefault('edition_start_date', config.get('edition_start_date', briefing['date']))
        briefing = prepare_briefing(briefing)
        validate_briefing(briefing)
        enforce_recency(briefing, now, args.hours)
        if not args.collect_only:
            require_minimum_video_stories(briefing)
        output = (args.output or ROOT / 'outputs' / now.strftime('%Y-%m-%d_%H%M%S_%f')).resolve()
        if (output / 'daily.mp4').exists() or (output / 'briefing.json').exists():
            raise ValueError('该目录已有日报，请指定新的 --output，避免覆盖已有成片或文字稿。')
        export_text(briefing, output)
        if not args.collect_only:
            render(briefing, output, args.voice or config.get('voice', 'zh-CN-XiaoxiaoNeural'), args.tts,
                   args.rate if args.rate is not None else config.get('speech_rate', 10),
                   pitch_hz=args.pitch if args.pitch is not None else config.get('speech_pitch_hz', -8),
                   warm=config.get('speech_warmth', True),
                   english_voice=config.get('english_voice', 'zh-CN-XiaoxiaoNeural'),
                   scene_lead_in_seconds=config.get('scene_lead_in_seconds', 0.25),
                   background_music_volume=config.get('background_music_volume', 0.42),
                   transition_click_volume=config.get('transition_click_volume', 0.32),
                   search_time=now)
        write_preview(briefing, output)
        print(f'完成：{output / "index.html"}', flush=True)
        if args.open and os.name == 'nt':
            os.startfile(output / 'index.html')
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f'生成失败：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
