import json, sys, datetime, socket
import feedparser

socket.setdefaulttimeout(25)
CFG = json.load(open('/home/ubuntu/projects/ai_dailyreport-20260927-clean/config.json'))
# 窗口起点：北京时间 2026-10-04 00:00 -> UTC 10-03 16:00
START = datetime.datetime(2026, 10, 3, 16, 0, tzinfo=datetime.timezone.utc)

def when(e):
    for k in ('published_parsed', 'updated_parsed'):
        t = e.get(k)
        if t:
            return datetime.datetime(*t[:6], tzinfo=datetime.timezone.utc)
    return None

rows = []
for src in CFG['sources']:
    name, url, kind = src.get('name'), src.get('url'), src.get('type')
    if kind in ('hf_papers', 'github_releases'):
        continue
    try:
        d = feedparser.parse(url, agent='Mozilla/5.0')
    except Exception as exc:
        print(f'!! {name}: {type(exc).__name__} {exc}')
        continue
    hits = []
    for e in d.entries[:40]:
        t = when(e)
        if t and t >= START:
            hits.append((t, e.get('title', ''), e.get('link', '')))
    flag = 'OK ' if hits else ('-- ' if d.entries else 'XX ')
    print(f'{flag}{name}: entries={len(d.entries)} in-window={len(hits)}')
    rows.extend((name, t, ti, l) for t, ti, l in hits)

print('\n===== 窗口内条目（按时间倒序） =====')
for name, t, ti, l in sorted(rows, key=lambda r: r[1], reverse=True):
    print(f'[{t:%m-%d %H:%M}Z] {name} | {ti}\n         {l}')
