# 任务：摘要门"拒绝即停放"（P1-A）

项目：`~/projects/ai_dailyreport-20260927-clean`（AI 日报视频流水线）。改动必须是**纯增量**：自动成片路径（`stories`）与现在**逐字一致**，只多出一份"被摘要门拒掉的候选"清单供人工写稿用。

先读这些再动手：`dailyreport/collect.py`（重点 `_summary`、`english_summary` 的调用点、`stage='summary_rejected'` 的两处、except 分支里 `stats['summary_rejected'] += 1` 的地方、`recently_broadcast` 过滤段）、`dailyreport/international.py:226 english_summary`、`dailyreport/broadcast_log.py`（复用 `url_fingerprint`）、`dailyreport/__main__.py` 的 `export_text`、`tests/test_collect.py`、`outputs/2026-09-29_081351_190456/briefing.json`（现成结构参考）。

## 要做的

### 1. 摘要门命中时"停放"而不是丢弃

- 摘要门 = 走到 `stage = 'summary_rejected'` 之后抛出的失败（`english_summary` 的四类 ValueError、`official_model_release` 缺模型名/特性、`concrete_news` 不通过、`single_page_layout` 容量不通过，以及该阶段的 `translate_to_chinese` 失败）。**只有这一阶段的失败进停放区**；`off_topic`、`date_rejected`、`fetch_failures`、`source_cap_skipped`、预算耗尽等更早阶段的原因**不进**。
- 停放条目字段：`{title, source_name, source_url, published, event_date, event_date_evidence, reason, snippet}`。
  - `title` 用原始标题（不做机翻）。
  - `reason` = 捕获到的异常文本原文。
  - `snippet` = 原始正文（或 feed abstract）前 200 字符，空白折叠成单空格；取不到就空字符串，**不要**因此抛错。
  - `published`/`event_date`/`event_date_evidence` 有就填，没有填空字符串。
- 去重与上限：同一条（`url_fingerprint(source_url, title)`）在同一次运行里只停一次；**每个来源最多 3 条**、**总数最多 30 条**，按 `event_date`（缺失则 `published`）从新到旧取；被上限挤掉的计入新统计键 `summary_parked_overflow`。
- `collection_stats` 新增键：`summary_parked`（实际停放的条数）、`summary_parked_overflow`。**`summary_rejected` 的语义不要动**（仍然统计所有摘要门失败次数）。
- `briefing` 顶层新增键 `summary_parked`（**永远存在**，没有就空列表）。
- 复用 `dailyreport/broadcast_log.py` 的 `url_fingerprint`，不要再写一份归一化逻辑。

### 2. 让停放清单出现在 report.md

`dailyreport/__main__.py` 的 `export_text` 里增加一节：非空时输出 `## 摘要门停放候选`，逐条 `- <event_date>｜<source_name>｜<title>｜<reason>｜<source_url>`（最多 30 条），让它在 `report.md` 里可读。

### 3. 测试 `tests/test_summary_parked.py`

至少覆盖：①摘要门失败时该条进入 `summary_parked` 且**不**出现在 `stories` 里 ②每源上限 3 与总数上限 30 生效、超出的计入 `summary_parked_overflow` ③同一 URL/标题不重复停放 ④非摘要门原因（日期不合格、off_topic）不进停放区 ⑤`briefing` 永远含 `summary_parked` 键 ⑥原文缺失/为 None 时不崩（snippet 为空串）。用现有的 mock/fixture 风格，别真联网。`tests/test_collect.py` 里那个"键集合必须精确相等"的断言按新契约更新即可。

## 硬约束

- 不改 `dailyreport/render.py`（尤其 ffmpeg 编码参数）、不改 `dailyreport/recency.py`、不新增第三方依赖。
- 不改 `data/*.json` 的既有内容，不删 `outputs/` 下任何东西。
- 保持每个文件原有的换行风格（部分是 CRLF），改哪行动哪行，不要整文件重写换行。
- 中文注释、中文输出，风格与现有一致。
- **回归底线**：`pytest` 必须全绿，且现有 197 个用例一个都不能因你而改行为（除上面那条键集合断言）。

## 收工前必须实跑并把输出贴进报告

```bash
cd ~/projects/ai_dailyreport-20260927-clean
.venv/bin/python -m pytest -q                      # 基线 197 passed，必须全绿

export DEEPSEEK_API_KEY=$(cat /tmp/.ds_key)
export ALL_PROXY=socks5h://127.0.0.1:10808 HTTP_PROXY=socks5h://127.0.0.1:10808 HTTPS_PROXY=socks5h://127.0.0.1:10808
.venv/bin/python -m dailyreport --collect-only --hours 120 --limit 10   # 约 6 分钟，等它跑完，不要中断
```

跑完后用 python 打印：`collection_stats` 全量、`len(summary_parked)`、停放区前 5 条的 `event_date / source_name / title / reason`（标题截 40 字），以及 `len(stories)`。把这段输出原样贴进报告。

## 报告里必须包含

①改动/新增文件清单 ②pytest 的 summary 行 ③上面那次真实采集的统计与停放区前 5 条 ④**你没有做到或不确定的地方**（尤其是：自动路径是否真的一条都没变、你如何证明的）。
