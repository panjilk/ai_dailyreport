# tech-news-digest 接入说明

当前项目默认启用 tech-news-digest 的补充采集。它负责发现候选；原项目继续检查近五个北京时间自然日、事件日期、新闻具体性、中文摘要和大模型播放优先级。正式视频至少五条，不用旧闻或模糊评论补数。

## 运行

```powershell
# 先收集新闻和待审线索
.\run.ps1 -CollectOnly

# 按现有流程采集并生成视频
.\run.ps1
```

每次使用新的输出目录。正式输入保存为 `briefing.json`；渠道运行状态为 `collection-status.json`；待审线索为 `review-candidates.json`。原始合并数据、各渠道结果、状态及有效配置保存在该次输出的 `tech-news-digest/` 中。新闻筛选失败时也保留采集记录，供继续核实；不能把候选数量当成正式新闻条数。

## 实际启用的渠道

| 渠道 | 配置 | 默认行为 |
| --- | --- | --- |
| RSS | Google AI、Gemini、Google Research、The Decoder、Interconnects | 无接口密钥可运行；回到原文后再摘要及核实事件 |
| GitHub | OpenAI、Anthropic、Gemini SDK，vLLM，SGLang | 可无密钥抓取；保留 REST 完整版本说明和稳定版本标记，再走具体性检查；Atom或其他证据不完整的条目只作待审线索 |
| X | OpenAI、Anthropic、Google DeepMind、Google AI、Tibo、Sam Altman、Demis Hassabis、DeepSeek、Qwen、Kimi | 有对应密钥才运行；所有社交帖先待审 |
| 网页搜索 | OpenAI、Claude、Gemini、DeepSeek、GLM、Qwen、Kimi、小米 MiMo 与 Codex | 有搜索密钥才运行；搜索摘要只作线索 |

原项目中文 RSS、OpenAI News、Google DeepMind 等来源继续参与收集。Anthropic 官网新闻使用独立适配器，因为其旧 RSS 返回 404；列表仅用于发现文章，文章 `article:published_time` 或 JSON-LD `datePublished` 必须带时区，修改日期不能替代发布日期。

## 接口密钥

通过运行进程的环境变量或项目根目录 `.env.local` 配置，不写入来源配置、代码或归档。可将 `.env.example` 复制为 `.env.local` 后填写。项目会自动读取该文件并传给采集子进程；已有非空环境变量优先，不修改主进程或系统环境。只接受采集密钥和后端选择变量，不执行文件中的任何命令。缺少密钥的渠道标记为 `skipped_missing_credentials`，不解释成当天没有消息。

| 变量 | 用途 |
| --- | --- |
| `X_BEARER_TOKEN` | X 官方接口；与第三方 X 接口任选其一 |
| `TWITTERAPI_IO_KEY` | 上游支持的第三方 X 接口 |
| `TAVILY_API_KEY` | 网页搜索；与 Brave 任选其一 |
| `BRAVE_API_KEY` / `BRAVE_API_KEYS` | Brave 网页搜索 |
| `GITHUB_TOKEN` | 可选，提高 GitHub 请求额度 |

空白样例默认设置 `TWITTER_API_BACKEND=twitterapiio` 和 `WEB_SEARCH_BACKEND=tavily`。如果改用 X 官方接口，需改为 `TWITTER_API_BACKEND=official` 并填写 `X_BEARER_TOKEN`；改用 Brave 时需改为 `WEB_SEARCH_BACKEND=brave` 并填写 Brave 密钥。也可将后端设置为 `auto`，让程序按已配置的密钥选择；不必同时申请所有供应商。

接口可能按供应商规则计费；项目不会替你申请或购买接口。`.env.local` 已被 Git 忽略；手工压缩项目时仍必须排除 `.env`、`.env.local` 等密钥文件，只携带空白 `.env.example`。新主机需自行填写密钥。不要把实际密钥发到聊天、提交 Git 或放进分享包。

## 审稿规则

OpenAI、Anthropic/Claude、Google/Gemini、DeepSeek、GLM、Qwen、Kimi、小米 MiMo 等具名大模型相关的具体变化优先，模型版本发布和能力升级排在其他 AI 新闻前。每条应说明谁做了什么、具体改变、影响及来源证据。社交投票必须核对问题、选项、截止时间和上下文，只能按征询意见描述，不能改写成已经执行的决定。

审核 `review-candidates.json` 中的原帖/官网链接，核实发布日期和实际事件日期，去除同一事件的重复候选，再将中文总结编辑进 `briefing.json`，提供 `event_date` 与 `event_date_evidence`。编辑输入仍由项目再次执行时效和至少五条检查：

```powershell
.\run.ps1 -InputFile outputs/本次目录/briefing.json
```

本接入只使用上游的数据采集脚本；视频和文字稿采用本项目的既有规则。直接使用上游 skill 生成其独立 digest 时，应另按其 `references/digest-prompt.md` 审稿与验证流程执行。

## 迁移与关闭

打包必须包含 `vendor/tech-news-digest/`（保留 MIT LICENSE）、`vendor/tech-news-digest.UPSTREAM.json`、`config/tech-news-digest/`、`dailyreport/tech_digest.py`、`dailyreport/official_news.py` 与主项目源码。不会依赖本机 Codex 全局技能路径。版本固定为 `c3aeafb940221debd597ed2963dd783755757f4c`，避免不同主机自动下载不同版本。

项目副本包含少量适配补丁：Windows缓存路径、X完整原文和投票字段、GitHub正式版本元数据，以及 RSS 原始时区校验和扩大窗口时的缓存重取。具体记录在 `vendor/tech-news-digest.UPSTREAM.json`。X字段参考 [X官方接口文档](https://docs.x.com/x-api/users/get-posts)，实际账号采集仍需要有效接口密钥。

缓存保存在项目 `outputs/.tech-news-digest-state/`，迁移时可以不带。接口密钥需在新主机自行配置。`config.json` 的 `tech_news_digest.enabled` 设为 `false` 可关闭补充管线，继续使用原项目采集。此接入未建立定时任务；需要每天无人值守运行时再配置调度。

## 在另一台电脑只采集文字

已经克隆项目的电脑先在项目目录执行 `git pull --ff-only`；如本地修改发生冲突，先保存并处理冲突，不强制覆盖。首次安装需要 Git、Python 3.10+ 和联网。不要复制旧电脑的 `.venv`，在新电脑重新建立环境。

Windows PowerShell：

```powershell
# 首次克隆；已有项目副本则只需更新，不重复克隆
git clone https://github.com/panjilk/ai_dailyreport.git
cd ai_dailyreport

# 仅在 .env.local 不存在时复制，避免覆盖已配置的密钥
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
notepad .env.local

# 填入自己的 Tavily / twitterapi.io 密钥，保存后运行
.\run.ps1 -CollectOnly

# 可选：小额验证两个接口，会各发送一次请求
.\.venv\Scripts\python.exe scripts\check_api_access.py
```

`-CollectOnly` 不生成音频或视频。成功输出写入新的 `outputs/日期_时间/`，包含 `report.md`、`script.txt`、`briefing.json` 和待审候选。采集或翻译失败时，查看终端错误与该次 `tech-news-digest/` 下的原始候选和状态；不要将失败当成当天没有新闻。

Linux/macOS 不使用 `run.ps1`，在项目目录运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 仅在 .env.local 不存在时复制，然后用本机编辑器填写密钥
test -e .env.local || cp .env.example .env.local
# 即使只采集文字，摘要长度检查也会用到字体；替换为实际中文字体路径
export DAILYREPORT_FONT=/absolute/path/NotoSansCJK-Regular.ttc
.venv/bin/python -m dailyreport --collect-only
```

`data/manuscripts/2026-10-12.md` 是已经核实、人工编辑的中文文稿，可以直接阅读或复制，不是 `--input` 所需的 JSON。新增采集功能负责发现候选，自动正文仍使用规则摘要及翻译；X 和搜索线索需要继续审稿。相同代码不保证自动生成与这份精编稿完全相同的文字，实时来源、运行时间、接口权限、限流和翻译服务都会影响结果。
