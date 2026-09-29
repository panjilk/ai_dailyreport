# 任务：采集并发化（P1-C）

项目：`~/projects/ai_dailyreport-20260927-clean`（AI 日报视频流水线）。

## 现状与目标

一次全量采集墙钟 ~229 秒，而 CPU 只用了 ~10 秒——几乎全在等 I/O。已知耗时分布（改前实测）：
- 26 个订阅源的抓取：串行
- 正文抓取：串行（受 `article_request_budget` 限制）
- **英文翻译：串行，183 次 DeepSeek 调用 × ~0.7 秒 ≈ 130 秒（最大的一块）**

目标：在不改变**选题结果与顺序**的前提下，把墙钟压到 100 秒以内。

## 铁律：结果必须与串行版本逐字一致

- `stories` 的**集合与顺序**、`excluded`/停放区的内容、`collection_stats` 里除新增计时键以外的计数，都必须跟串行版本完全一样（对同一份输入）。
- 只并行化**纯 I/O**：源抓取、翻译请求。**绝不并行化选题、排序、优先级、预算判断、去重、摘要门**这些逻辑。
- 并行结果必须**按输入顺序回位**（按索引收集后再按索引排序），不允许"谁先返回谁先入队"。
- 错误列表 `collection_errors` 的顺序也要稳定（按源在 config 里的顺序、按候选的排名索引）。

### 哪些允许并行、哪些不要碰

- **允许**：①26 个源的 feed 抓取（互相独立） ②同一个候选里的多条翻译（标题/各条要点）以及不同候选之间的翻译请求。
- **谨慎**：正文抓取（`article_requests`）。它对 `article_request_budget` 的消耗是**惰性且按排名顺序**的，还有 `deferred` 第二轮遍历。这一轮**不要**改成预取，保持按排名顺序串行消费预算——如果你认为预取能保证结果一致，请先写出你对"结果一致"的论证再动手，否则保持串行。

## 要做的

### 1. 并发原语（新增 `dailyreport/concurrency.py`）

- `run_ordered(items, worker, workers, on_error=None) -> list`：按 `items` 顺序返回结果；`workers` 上限内并发；任一任务的异常要能按位置返回给调用方（不要吞掉、不要让整个批次互相污染）；内部用 `concurrent.futures.ThreadPoolExecutor`。
- 并发数从 `config.json` 新增键 `collection_concurrency` 读取（默认 6，允许 1–16 的整数，1 表示退回串行；非法值报错）。环境变量 `COLLECT_CONCURRENCY` 可覆盖（便于压测）。

### 2. 并发化源抓取

`dailyreport/collect.py` 里遍历 `config['sources']` 的那段：把每个源的"抓取+解析+产出行"放进线程池并发跑（上限=并发数），**按源在配置里的顺序**把 rows 和 errors 合并回主流程。
- `data/source_health.json` 的读写要加锁（模块级 `threading.Lock`），避免并发写坏。
- 每个线程用自己的 `requests.Session`（`threading.local()`），不要跨线程共用 Session。

### 3. 并发化翻译（最大收益）

- `translate_to_chinese()` 内部按 chunk 的翻译请求允许并发（同一句的多个 chunk 并发，返回后按顺序拼接）。
- 更进一步：**在 `collect.py` 侧一次性批量并发**翻译同一候选的标题+要点（这些文本互相独立），但必须保证拼接顺序与串行一致。
- 缓存 `data/translation_cache.json`：加锁，避免并发读写互相覆盖；成功翻译后**合并写回**（不要在每次调用里全部重写、也不要丢别人的条目）。
- 并发数同上（默认 6），不要对 DeepSeek 打超过 8 并发。

### 4. 分阶段计时（证据，也方便以后继续优化）

- `collection_stats` 新增 `timings`：`{'feeds_seconds':…, 'articles_seconds':…, 'translation_seconds':…, 'total_seconds':…}`（用 `time.perf_counter()`，只做统计，不影响逻辑）。
- `report.md`（`dailyreport/__main__.py` 的 `export_text`）把 `timings` 打印出来。

### 5. 测试 `tests/test_concurrency.py`（新增，≥6 条）

①`run_ordered` 按输入顺序返回（让先提交的睡久一点，断言顺序不乱）②并发上限被遵守（用计数器断言同时进行数 ≤ workers）③workers=1 时退化为串行且结果一致 ④异常按位置返回、不影响其它任务 ⑤非法并发值报错、`COLLECT_CONCURRENCY` 覆盖生效 ⑥并发下的翻译缓存不丢条目（先清空缓存目录，模拟多线程写回，断言条目数正确）。

## 硬约束

- 不改 `dailyreport/render.py`（尤其 ffmpeg 编码参数）、不改 `recency.py`、不新增第三方依赖（标准库的 `concurrent.futures`/`threading` 允许）。
- 不改 `data/*.json` 既有内容（`broadcast_log.json`、`source_health.json`、`translation_cache.json` 由程序自己维护）。
- 保持各文件原有换行风格（多为 CRLF）；中文注释、中文输出。
- 现有 219 个用例必须全绿（除上面明确允许的新增/改写），**不许删用例凑绿**。

## 收工前必须实跑并把输出贴进报告

```bash
cd ~/projects/ai_dailyreport-20260927-clean
.venv/bin/python -m pytest -q                     # 基线 219 passed

export DEEPSEEK_API_KEY=$(cat /tmp/.ds_key)
export ALL_PROXY=socks5h://127.0.0.1:10808 HTTP_PROXY=socks5h://127.0.0.1:10808 HTTPS_PROXY=socks5h://127.0.0.1:10808

rm -f data/translation_cache.json                 # 冷缓存，才看得出真实收益
date; time .venv/bin/python -m dailyreport --collect-only --hours 120 --limit 10; date
date; time .venv/bin/python -m dailyreport --collect-only --hours 120 --limit 10; date   # 热缓存
```

跑完打印：每轮的总墙钟与 `timings`、`collection_stats` 全量、`len(stories)`、以及**两轮 stories 的
`nav_label` + 标题 sha1 列表**（贴出来证明两轮选题逐字一致）。

另外做一次**并发正确性对照**：用同一份输入分别跑 `COLLECT_CONCURRENCY=1` 和 `=6`，
断言两者的 `stories`（标题+指纹）与停放区内容完全一致，把对照结果贴出来。

## 报告里必须包含

①改动/新增文件清单 ②pytest summary 行 ③冷/热缓存两轮的墙钟与 `timings` 对比 ④并发=1 与并发=6 的结果一致性对照
⑤两轮 stories 指纹列表 ⑥**你没有做到或不确定的地方**（尤其：正文抓取你为什么保持串行、并发下有没有你没能验证的竞态）。
