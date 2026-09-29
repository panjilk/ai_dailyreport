# 任务：把英文→中文翻译从 MyMemory 换成 DeepSeek（P1-B）

项目：`~/projects/ai_dailyreport-20260927-clean`（AI 日报视频流水线）。

## 背景（真实故障，必须先理解再动手）

`dailyreport/international.py` 的 `translate_to_chinese()` 现在打免费公共接口
`https://api.mymemory.translated.net/get`（第 15 行 `TRANSLATION_URL`）。匿名额度约 1000 词/天，
一天跑 2–3 次全量采集就把配额打爆，之后**每个英文条目都返回 429 → 整条被拒 → 采集产出 0 条**。
2026-09-29 已复现：`outputs/2026-09-29_143542_137988/report.md` 里 `selected: 0`，
`collection_errors` 里几十条 `429 Client Error ... api.mymemory.translated.net`。
同时这个接口的机翻质量差（`克劳德十四行诗5.5` 这种），必须一起换掉。

## 要做的

### 1. 换后端：DeepSeek

- 参照仓库里已有的 DeepSeek 用法：`tools/rewrite_narration.py`（`https://api.deepseek.com/v1/chat/completions`，模型 `deepseek-chat`，key 取环境变量 `DEEPSEEK_API_KEY`）。
- 重写 `translate_to_chinese()`：
  - 保持"第二个位置参数可注入 HTTP 调用方"这个测试接缝（现有测试用 `translate_to_chinese(text, fake_call)` 注入，见 `tests/test_international.py:219`），注入对象换成 POST 形式；该测试按新契约更新即可。
  - 系统提示要求：只输出译文、不要解释、不要加引号；**术语表里的名称保留原文**；保持数字、百分比、版本号、产品名不变；不得添加原文没有的信息。
  - `temperature` 用 0（或最低），`timeout=30`。
  - **代理：DeepSeek 必须直连**——用 `requests.Session()` 并设 `trust_env = False`，不要让它走 `ALL_PROXY`（采集英文源需要代理，但 DeepSeek 走代理解析不稳）。若直连失败，再退回一次"带环境代理"的会话重试。
  - 重试：429 / 5xx / 超时 → 最多 3 次，退避 1s / 3s / 7s；最终仍失败就抛 `ValueError`（调用方会把该条停放到 `summary_parked`，这是期望行为，不要回退英文）。
  - 校验返回值：必须含中文字符、不能与原文相同，否则抛错。
  - `DEEPSEEK_API_KEY` 缺失 → 抛 `ValueError('缺少 DEEPSEEK_API_KEY，无法翻译英文条目')`，不要静默英文回退。
- 删除 MyMemory 相关代码与 `MYMEMORY_EMAIL` 逻辑；`_translation_chunks()` 保留但把分块上限从 450 提到 1200 字符。

### 2. 本地翻译缓存 `data/translation_cache.json`

- 键：`sha256(归一化后的原文)`（归一化 = 折叠空白）；值：`{"zh": 译文, "model": "deepseek-chat", "ts": ISO 时间}`。
- 命中直接返回，**不发请求**；每次成功翻译后写回（临时文件 + 原子替换）。
- 文件不存在 / JSON 损坏 / 值缺字段 → 按空缓存处理并给出 warning，**不抛异常**。
- 上限 5000 条，超出按 `ts` 从旧到新淘汰。

### 3. 术语表 `data/glossary.json`

- 新建该文件，内容为 `{"keep_original": ["GPT-6", "GPT-6 Sol", "Claude Sonnet 5.5", "Claude Opus 5.5", "Gemini 3.8", "Kimi K3", "GLM-5.3", "DeepSeek", "Qwen", "MiniMax", "ElevenLabs", "LongCat", "Astra 6.1", "Codex", "Hugging Face", "arXiv", "NVIDIA", "AMD", "Shopify", "Terminal-Bench"]}`（可按实际补充）。
- 提示词里带上这个列表；译文返回后检查：原文里出现的术语在译文里必须原样出现，缺失则**重试一次**并加强提示；仍缺失就接受译文，但在 `collection_errors` 记一条 warning（不要因此丢弃整条新闻）。

### 4. 统计与文档

- `collection_stats` 新增：`translation_api_calls`、`translation_cache_hits`、`translation_failures`。
- `README.md:89` 那段关于 MyMemory 的说明改写为 DeepSeek + 缓存 + 术语表的实际行为。

### 5. 测试 `tests/test_translation_deepseek.py`（新增，≥8 条）

①缓存命中不发请求 ②翻译成功后写入缓存并可重载 ③缓存损坏不崩 ④429 后重试成功（断言调用次数）⑤持续 429 最终抛错 ⑥缺 `DEEPSEEK_API_KEY` 抛错 ⑦术语缺失触发一次重试 ⑧返回值无中文/与原文相同 → 抛错 ⑨超长文本按 ≤1200 字符分块 ⑩直连会话 `trust_env is False`。`tests/test_international.py` 里那两个翻译相关的用例按新契约改写，**不许删掉用例凑绿**。

## 硬约束

- 不改 `dailyreport/render.py`（尤其 ffmpeg 编码参数）、不改 `recency.py`、不新增第三方依赖（只用标准库 + `requests`）。
- 不改 `data/briefing-*.json` 的既有内容；`data/translation_cache.json`、`data/glossary.json` 是新增文件（缓存文件不要提交进 git，改 `.gitignore`）。
- 保持各文件原有换行风格（多为 CRLF）。
- 中文注释、中文输出，风格与现有一致。

## 收工前必须实跑并把输出贴进报告

```bash
cd ~/projects/ai_dailyreport-20260927-clean
.venv/bin/python -m pytest -q                      # 基线 204 passed，必须全绿（改契约后总数不得减少）

export DEEPSEEK_API_KEY=$(cat /tmp/.ds_key)
export ALL_PROXY=socks5h://127.0.0.1:10808 HTTP_PROXY=socks5h://127.0.0.1:10808 HTTPS_PROXY=socks5h://127.0.0.1:10808

# 第一次：应真的走 DeepSeek
date; .venv/bin/python -m dailyreport --collect-only --hours 120 --limit 10; date
# 第二次：应大量命中缓存（对比 translation_cache_hits / 耗时）
date; .venv/bin/python -m dailyreport --collect-only --hours 120 --limit 10; date
```

每次跑完打印：`collection_stats` 全量、`len(stories)`、`collection_errors` 里 `429` 的条数（必须是 0）、
以及入选条目的**中文标题前 5 条**（证明翻译质量与术语保留）。

## 报告里必须包含

①改动/新增文件清单 ②pytest summary 行 ③两次真实采集的 stats 对比与耗时 ④5 条中文标题样本
⑤**你没有做到或不确定的地方**（尤其是：DeepSeek 直连是否真的绕过了代理、你的证据是什么）。
