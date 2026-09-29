# AI Daily Video Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent research/review and direct implementation for the coupled rendering pipeline.

**Goal:** Deliver a working news-to-Chinese-video tool and an actual first MP4 without scheduling.

**Architecture:** RSS collection produces source-attributed story JSON. A renderer converts stories to card images, speech, timed subtitles and H.264/AAC video. An independently researched first edition uses the same renderer.

**Tech Stack:** Python 3.12, requests, feedparser, BeautifulSoup, Pillow, edge-tts, imageio-ffmpeg, pytest; Windows SAPI fallback.

**Spec:** docs/superpowers/specs/2026-09-11-ai-daily-video-design.md

## Global Constraints

- No scheduled tasks, no external publication.
- 1920×1080, Chinese narration, readable subtitles, original source links and dates.
- No undisclosed old/future news or fabricated source verification.
- All files stay in this new project directory; no pre-existing Git repository to isolate.

## Task 1 — Source collection and first-edition research

Files: `dailyreport/collect.py`, `config.json`, `tests/test_collect.py`, `data/briefing-2026-09-11.json`.

Interface: `select_recent(items, now, hours, limit) -> list[dict]`; `collect(config, now, hours, limit) -> dict`.

- [x] Write regression cases for old/future/missing timestamps, timezone offsets and duplicate tracking URLs. Run `python -m pytest tests/test_collect.py` to confirm missing behavior.
- [x] Implement HTTP RSS fetches with timeouts and XML validation, readable article extraction, deterministic Chinese sentence selection and explicit extractive-summary labels.
- [x] Independently verify first-edition stories with primary-source web research, saved URLs and dates. Expand the labelled date window only when needed.
- [x] Run targeted tests and a real network collect command; inspect source failures and content dates.

## Task 2 — Video rendering

Files: `dailyreport/render.py`, `dailyreport/speech.ps1`, `tests/test_render.py`.

Interface: `render(briefing, output, voice) -> Path`; `split_sentences(text, max_chars=28) -> list[str]`; `srt_time(seconds) -> str`.

- [x] Test independent literal cases: `srt_time(61.25) == '00:01:01,250'`, Chinese splitting preserves text, long title/card wrapping stays within width.
- [x] Implement overview and story card images with date/category/source strips, then per-sentence speech and exact duration-based subtitle timing.
- [x] Produce a timed card-image sequence and combine it with narration as H.264/AAC video; output SRT and JSON timing manifest.
- [x] Render complete prepared and automatically collected editions, then check decoding, dimensions, audio presence and subtitle/image layout.

## Task 3 — One-click packaging, complete edition, review

Files: `dailyreport/__main__.py`, `run.ps1`, `生成日报.cmd`, `requirements.txt`, `README.md`, output preview files.

- [x] Add CLI `python -m dailyreport [--input PATH] [--hours 24] [--limit 8] [--collect-only] [--output PATH]`.
- [x] Default path fetches current news; explicit input renders a source-attributed prepared edition. Never silently replay a cached edition as today's news.
- [x] Document online TTS behavior, fallback, installation, output paths, failure handling, and no scheduler.
- [x] Generate and inspect full first edition, run `python -m pytest`, decode video with FFmpeg and record results.
- [x] Independent review focuses on false freshness, incomplete audio, output corruption and one-click usability; fix concrete findings.

## Execution ledger

- Design accepted in conversation; user removed scheduling and requested implementation directly.
- Ruling: Proceed without another design/plan approval because the user already approved the concrete scope.
- Ruling: Use the empty named project workspace directly; there is no existing Git branch or working tree to protect.

- Complete: prepared 2026-09-11 edition (6 stories, 225.833 s) and live 2026-09-12 edition (6 stories, 232.333 s).
- Tests: 32 passed plus 10 parametrized subtests. Independent reviewer confirmed both prior P1 findings resolved.
- Ruling: Use keyword classification and source-only contiguous Chinese extracts by default, explicitly labelled; no model credentials available or required. Conservative rejection of correction/rumour contexts prevents stripping denials.
- Ruling: Retain source timestamps as supplied. A story outside the current window is excluded even if a publisher may have supplied an incorrect timezone.
- Fixed in real integration: punctuation-only speech chunk; transient speech retries; English word wrapping; Windows PowerShell silent dependency detection; standard 48 kHz AAC output.
- No scheduling, no hosting, no external publication or git branch operations were performed.
