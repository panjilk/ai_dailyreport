#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed sweep with --since (UTC ISO). Usage: python tools/feed_sweep_$(date).py 2026-10-04T10:00:00"""
import json, datetime, socket, sys
import feedparser
socket.setdefaulttimeout(30)
CFG = json.load(open('/home/ubuntu/projects/ai_dailyreport-20260927-clean/config.json'))
since = sys.argv[1] if len(sys.argv) > 1 else '2026-10-04T10:00:00'
START = datetime.datetime.fromisoformat(since)
if START.tzinfo is None:
    START = START.replace(tzinfo=datetime.timezone.utc)
srcs = CFG.get('sources') or CFG.get('feeds')


def when(e):
    for k in ('published_parsed', 'updated_parsed'):
        t = e.get(k)
        if t:
            return datetime.datetime(*t[:6], tzinfo=datetime.timezone.utc)
    return None


rows = []
for src in srcs:
    name, url, kind = src.get('name'), src.get('url'), src.get('type')
    if src.get('enabled') is False:
        print(f'-- {name}: disabled')
        continue
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
    print(f"{'OK ' if hits else '-- '}{name}: entries={len(d.entries)} in-window={len(hits)}")
    rows.extend((name, t, ti, l) for t, ti, l in hits)
print('\n===== 窗口内条目 =====')
for name, t, ti, l in sorted(rows, key=lambda r: r[1], reverse=True):
    print(f'[{t:%m-%d %H:%M}] {name} | {ti}\n    {l}')
