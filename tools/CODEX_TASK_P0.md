# 项目：~/projects/ai_dailyreport-20260927-clean（AI 日报视频流水线，Windows 移植到 Linux）

## 你的任务（P0 三项，全部做完再收工）

先读这几个文件确认结构，再动手：`dailyreport/collect.py`、`dailyreport/cli.py`、`config.json`、
`outputs/2026-09-29_081351_190456/{briefing.json,timeline.json,subtitles.srt}`、`tests/` 下现有测试。

### 1. 已播台账 broadcast ledger

- 新增 `dailyreport/broadcast_log.py`：
  - 指纹函数：`url_fingerprint(url, title)` —— 归一化（去空白、英文转小写、去标点）后取标题的 sha1 前 16 位；同一新闻不同转载 URL 只要标题归一化相同就该命中。
  - `append_edition(briefing: dict, log_path: Path)`：把本期每条 story 的 `{date, nav_label, title, source_url, fingerprint}` 追加写入 `data/broadcast_log.json`（结构自定，但要能按日期回查）。
  - `recent_fingerprints(log_path, editions=3)`：返回最近 3 期出现过的 fingerprint 集合与 URL 集合。
  - 容错：日志不存在、JSON 损坏、缺字段都不能抛异常，要降级为空集合并返回 `(set(), set(), warnings: list[str])` 之类的信息。
- 接入采集：`--collect-only` 时，命中的候选必须**不进入最终选题**，并写进 briefing.json 的新键 `recently_broadcast`：`[{title, source_url, appeared_date}]`；已有的 `collection_stats` 增加一个计数键 `skipped_recently_broadcast`。
- 生成视频成功写出 briefing 后，自动调用 `append_edition`（幂等：同一天同一 fingerprint 不重复写入）。
- 新增 `tests/test_broadcast_log.py`：至少覆盖 ①指纹稳定性（同标题不同空格的转载命中、不同标题不命中）②追加+重载 ③recent 过滤会排除命中候选 ④日志缺失/损坏不崩 ⑤同一天重复调用幂等。

### 2. 成片校验脚本 `tools/verify_video.py`

`python3 tools/verify_video.py <成片目录>`，读该目录里的 `daily.mp4`、`briefing.json`、`timeline.json`、`subtitles.srt`、`assets/frame-*.png`。检查项：

1. ffprobe：视频流 h264、分辨率 1920x1080、帧率 24、时长与字幕最后一句结束时间相差 ≤1.5 秒、存在音频流。
2. 音频电平：ffmpeg `volumedetect` 的 `mean_volume` 必须 > -40 dB（防静音成片）。
3. 每条新闻的画面日期一致性：用该条对应的 `assets/frame-*.png` 做 OCR（`tesseract`），断言该条的 `event_date`（如 `2026-09-28`）出现在画面文字里，且要点里的日期文字与 `event_date` 一致。
   - **本机没有装 tesseract**：检测不到就跳过 OCR 类检查，并**明确打印"OCR 检查已跳过（未安装 tesseract）"**，绝不静默通过。
4. 条数与帧数、字幕条数与 `briefing.json` 一致。
- 退出码：全部通过 `0`；有硬失败 `1`（逐条打印中文原因）；仅 OCR 被跳过 `2`。
- 报告用中文、简洁（一行一个检查项 + 结论）。
- 新增 `tests/test_verify_video.py`：只测纯逻辑（日期断言比较、时长容差、退出码映射、缺文件报错），用假数据/mock，**不要在测试里依赖 ffmpeg 或真实视频**。

### 3. 清理死源 + 失败告警

- `config.json` 的 `sources` 里这三个源长期失败，请逐个实测后处理（允许的改动仅限于这些条目）：
  - `Anthropic News`（`https://www.anthropic.com/news/rss.xml`，实测 HTTP 404）
  - `小米AI实验室`（`https://hyper.ai/feed`，XML 破损：`not well-formed (invalid token): line 1, column 76314`）
  - `极客公园`（偶发 Read timeout）
  - 处理方式二选一：找到可用的官方订阅地址就换；确认没有就 `enabled: false` 并在条目旁加 `"disabled_reason": "..."`。**先实测再决定**，不要凭印象。
- 新增 `dailyreport/source_health.py`：把每个源的连续失败次数累计到 `data/source_health.json`（键：源名；值：`{consecutive_failures, last_error, last_checked}`）；成功即清零；连续失败 ≥3 次时在采集输出里打印显眼的 `[源疑似失效]` 警告并在 briefing.json 增加 `stale_sources` 列表。
- 新增 `tests/test_source_health.py`：覆盖累计、成功清零、达阈值触发告警、文件损坏不崩。

## 硬约束

- **不得修改** `dailyreport/render.py` 里 ffmpeg 编码参数（`-preset slow -crf 14 -x264-params keyint=...`），那是刻意调好的。
- 不新增第三方依赖（标准库 + 已有的 requests 即可）。
- 不删除、不改写 `data/briefing-*.json` 已有内容；只新增文件。
- 保持每个文件原有的换行风格（部分文件是 CRLF），改动不要整文件重写换行。
- 中文注释与中文输出，风格跟现有代码一致。
- 不要动 `outputs/` 下的成片。

## 收工前必须自己验证并把结果贴出来

```bash
cd ~/projects/ai_dailyreport-20260927-clean
.venv/bin/python -m pytest -q          # 基线 184 passed，必须全绿，且新增测试后数量应增加
python3 tools/verify_video.py outputs/2026-09-29_081351_190456
.venv/bin/python -c "import json,glob;[print(glob.glob('data/broadcast_log.json'))]"
```

最终报告里给出：①新增/修改的文件清单 ②pytest 的最终 summary 行 ③verify_video 的完整输出与退出码
④三个死源的实测结论（用了什么命令、返回什么） ⑤你**没有**做到或不确定的地方。
