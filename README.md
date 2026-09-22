# AI 日报视频

自动获取大模型迭代与评测新闻，抽取中文要点，生成 **1080p 横屏 MP4、中文配音、画内字幕、文字日报和来源链接**。画面采用米白背景、橙色标题、分类卡片与章节导航。

**不含定时任务。** 每次手动运行生成一期，不自动上传或发布。

## 已生成的成片

**最新扩充版**：`outputs/video-20260919-expanded-v2/index.html`，约2分22秒；收录9月15日至19日窗口内的10条资讯，先排热点档位，同档按发布时间从新到旧。使用晓伊自然语速，每条短总结完整读完，画面保留详细要点。9条来自本次采集，1条论文复用本日早前已抓取的来源记录。

以下早期版本仅作历史存档，不能直接作为当前日报导入；导入时仍会按本次北京时间近 5 个自然日窗口重新过滤。

- **最新：大模型单页版**：`outputs/2026-09-12-models-single-page/index.html`，2分49秒；ChatGPT、Claude、Gemini、DeepSeek四条，每条3点、1页，模型名导航。选题范围明确为9月1–12日的近期迭代与效果精选。

- **2026-09-12 完整快语速修正版**：`outputs/2026-09-12-complete-fast/index.html`，重新总结六条新闻，4分34秒；语速约为旧版1.3倍，全部要点完整显示和朗读，该版采用分页；最新规则改为每条一页。
- **2026-09-12 自动版**：`outputs/2026-09-12_101924_774524/index.html`，实时采集最近24小时，6条资讯，3分52秒，中文晓晓配音。
- **2026-09-11 编辑版**：`outputs/2026-09-11-release/index.html`，6条官方来源资讯，3分46秒；报道范围9月8–11日。

双击对应 `index.html` 可播放视频和跳转章节，`daily.mp4` 可直接导入剪辑软件。

## 直接使用

**时效硬限制：以本次搜查时间为准，只收录北京时间搜查当天及此前 4 个自然日的新闻，最早到第 5 个自然日零点。** 默认 `--hours 120`；实际起点取“当前时刻向前 120 小时”与“第 5 个自然日零点”中较晚的时间。条数不足不继续扩窗，也不用窗口外旧闻补齐。稿件的 `date` 不必是今天，但报道日期和事件日期都必须处于本次窗口内；不能以新转载日期替代旧事件日期。导入稿件须提供 `event_date`，过期或未来条目会被剔除并记录原因，全部不合格时停止生成。输入中的旧 `search_date` 不能绕过此检查。

双击 **`生成日报.cmd`**。程序获取北京时间近 5 个自然日的新闻，默认最多收录 10 条，完成后打开本地视频预览页。首次运行会在项目 `.venv` 中安装依赖，需要 Python 3.10 或更高版本和联网。

每次结果单独保存在 `outputs/日期_时间/`，已有日报不会被覆盖：

| 文件 | 内容 |
| --- | --- |
| `index.html` | 本地播放器、章节跳转、新闻卡片和下载入口 |
| `daily.mp4` | H.264 / AAC，1920×1080，24fps，含画内字幕 |
| `report.md` | 分类日报与完整来源 |
| `script.txt` | 各条资讯口播稿 |
| `subtitles.srt` | 可导入剪辑软件的字幕 |
| `briefing.json` | 本期输入，可编辑并重新制作 |
| `timeline.json` | 实际时间轴与配音引擎记录 |
| `cover.png` | 总览封面 |
| `narration.wav` | 独立旁白音频 |
| `assets/` | 卡片及分段配音素材 |

## 命令行

在项目目录用 PowerShell 执行：

```powershell
# 默认：抓取最新新闻并生成视频
.\run.ps1

# 默认近5个自然日、最多10条（最长回看120小时）
.\run.ps1 -Hours 120 -Limit 10

# 默认使用约1.1倍语速的温暖女声；也可单独调整语速和音高
.\run.ps1 -Rate 10 -Pitch -8

# 使用已审阅稿件；运行时会重新剔除超出本次近5天窗口的新闻
.\run.ps1 -InputFile outputs/你的采集目录/briefing.json

# 只采集文字，先审阅内容
.\run.ps1 -CollectOnly

# 导入文件的稿件日期可以不是今天，但新闻不能超出本次搜查窗口
.\run.ps1 -InputFile outputs/你的采集目录/briefing.json

# 已安装依赖时，也可直接调用 Python
.\.venv\Scripts\python.exe -m dailyreport --input outputs/你的采集目录/briefing.json --tts sapi
```

首次交付的编辑版素材收录 **2026年9月8–11日** 六条官方来源资讯，明确显示原文日期，并非六条都发生在9月11日。之后默认运行会重新采集，不会自动重播这份稿件。

## 新闻与摘要

默认 `topic_scope: all_ai`，收录所有与 AI 相关的新闻，包括国内外大模型迭代、产品功能、GPT/ChatGPT 用量重置、额度和订阅调整、论文评测、AI 政策监管、政治与社会影响、行业融资、人事、硬件及应用。无 AI 关联的普通政治或社会新闻不收录。GLM/智谱、Kimi/月之暗面、DeepSeek/深度求索等国内模型及其他中英文别名继续支持；可切回 `foundation_models` 仅看模型主题。

**选题优先级**：先按规则划分热点档位，再在同一档位内按发布时间从新到旧排列，较晚的消息继续后排；截取所需条数后，日报与成片保持这一顺序。最高档为大模型迭代、版本发布和能力升级；第二档包括用量、重置、额度、订阅、价格变化，以及重要的 AI 产品、安全、监管等动态；其余 AI 新闻进入普通档。这里的“热门”是基于新闻类型的编辑规则，不是网站浏览量。每条仍需符合近 5 个自然日时效、有来源及事件日期证据；政策通过、监管公告和额度重置等按各自实际发生日期核实。

- 默认启用 **IT之家 RSS、量子位 RSS、雷峰网 RSS、极客公园 RSS、Hugging Face 论文 API、arXiv cs.CL RSS、Transformers GitHub Releases API**，以及 OpenAI News、Google DeepMind、Hugging Face Blog、NVIDIA Blog 四个官方英文 RSS 和 TechCrunch AI。以上来源参考 [ai-daily-skill](https://github.com/geekjourneyx/ai-daily-skill)、[CloudFlare-AI-Insight-Daily](https://github.com/justlovemaki/CloudFlare-AI-Insight-Daily) 与 [ai-daily-briefing](https://github.com/Rion-Wu-tech/ai-daily-briefing) 的数据源设计，并在本项目中按 5 天窗口重新验证日期。官方英文 RSS 标记为 `official_article`，摘要明确注明发布方自述、尚未独立复核。
- 另启用 Simon Willison、Gary Marcus、Dwarkesh Patel、Gwern、Max Woolf、Giles Thomas、Sean Goedecke、Martin Alderson、Where's Your Ed At、LCamtuf 等 10 个英文技术博客。英文博客来自 [ai-daily-digest](https://github.com/vigorX777/ai-daily-digest) 收录的 Hacker News 社区高质量博客列表；本项目只选取 AI 内容较多的子集，并再次执行 AI 主题与标题可理解性过滤，跳过 `Quoting …`、`Note on …` 等脱离正文无法判断内容的微型条目。雷峰网、极客公园和英文 RSS 使用 Feed 内嵌正文或摘要。英文论文、版本和文章使用专门适配器，不套用中文正文规则。来源可在 `config.json` 中按 `name`、`url`、`type`、`content_kind`、`enabled`、`ai_only`、`max_stories` 管理。
- `max_stories` 是每个来源的优先入选上限，用于先保证来源多样性。默认优先上限为 IT之家 5 条、量子位 3 条、英文技术博客各 1 条，其余已配置来源各 2 条；如果其他来源没有足够合格内容，程序会继续按全局热点和发布时间顺序从暂缓候选中回填，直到达到 `--limit` 或没有可用新闻。`config.json` 可以添加 RSS/Atom 来源；`ai_only: false` 的综合来源会先过滤 AI 相关条目。
- `article_request_budget` 控制每次正文请求上限，默认40，允许1至100；在上限内继续检查后续候选，直到收录足够条数。`briefing.json` 的 `collection_stats` 与 `report.md` 记录主题不符、时间超窗、重复、正文失败、事件日期不合格、摘要失败、未检查候选和预算耗尽情况。没有任何合格新闻时，终端也会输出统计和失败原因。
- 日期识别支持“9 月 12 日”等含空格写法；排除计划、预告和否定语境，优先关联标题中对应模型。多个日期无法消歧时保守跳过，`event_date_evidence` 保存匹配的原文句子供审核。此规则抽取仍不等于人工事实核验。
- Atom 只有 `updated` 时可作为报道时间候选，仍须从正文核实实际模型事件日期。
- 自动摘要从中文正文选取完整句子，不需要大模型 API 密钥。标题和原文观点保留来源归属；它不会做深层推理或跨文献事实核验，句子衔接可能不如人工编辑稿自然。
- 排除缺少时区/时间、未来及窗口外的新闻；按 URL 与标题去重，不足指定条数时如实减少。原站时间有误的条目可能被排除。
- 单篇文章读取失败会跳过并记入 `report.md`。包含辟谣、纠正语境或无法保留归属限定的文章会保守跳过，因此可能漏掉部分值得报道的内容。没有合格资讯时明确失败，不用旧闻填充。
- 分类为规则判断，可能需要人工调整。可先 `-CollectOnly`，核实输出的 `briefing.json` 中 `event_date`、来源日期与正文，再用 `-InputFile` 制作视频。
- 英文论文、版本说明、官方公告和海外观点会先抽取完整英文句子及必要限制，再通过 MyMemory 翻译为中文。视频标题、画面要点和口播只使用中文；翻译失败或额度不足时整条跳过，不回退显示英文。`source_text` 仍保存英文原文供核验，`source_language: en` 标记原始语言，`language: zh` 标记成片语言。可设置 `MYMEMORY_EMAIL` 提高公共翻译服务的调用额度。超过单页容量的译文会跳过，不截断句子。
- 网站拦截、限流、RSS变更或正文结构变化可能影响采集；会记录失败原因，不将失败解释为当天没有新闻。

### 实际搜查与入选要求

程序遍历已配置的来源，并非搜索整个互联网；每个来源最多读取500条（GitHub最多100条，当前接口请求20个版本），先按热点档位、再按同档发布时间从新到旧排序，并按 URL 和标题去重。`max_stories` 先限制单一来源占比，其他来源不足时再按全局顺序回填。正文请求默认最多40次；预算耗尽后，仍会继续检查不需要额外正文请求的内嵌全文和版本说明候选。来源接口请求不计入正文预算。

1. **时效**：北京时间搜查当天及此前 4 个自然日，最早从第 5 个自然日零点开始；`--hours` 默认 120，可缩小但不能扩大这 5 个自然日窗口。报道日期和事件日期都必须合格，排除未来时间。
2. **主题**：默认覆盖 AI 相关政策政治、行业、产品、用量、硬件、论文等消息，优先大模型迭代，其次用量和订阅变化。综合新闻源检查标题或摘要前300字的 AI 关联；配置为 `ai_only` 的专业源按 AI 来源处理。`foundation_models` 是可选的窄范围模式。
3. **论文**：HF 使用 `paper.publishedAt`，不使用推荐日期；HF和arXiv候选都回到arXiv摘要页验证 `[v1]` 首次提交的带时区时间。修订、交叉列表或重新推荐不视为新论文。摘要只代表作者报告，不意味着已通过同行评审，也不意味着相关模型当天发布。
4. **版本**：GitHub 使用 `published_at`，排除草稿和预发布，不使用创建时间或最后编辑时间。框架新增模型支持不表述成模型首次发布。
5. **内容与证据**：保留来源、原文、时间依据、完整摘要及限制条件。无明确时间或无法提取摘要时跳过；不以旧闻补齐条数。统计和失败原因在终端及成功输出的文字日报中可查。

接口参考：[Hugging Face API](https://huggingface.co/docs/hub/en/api#get-apidailypapers)、[arXiv API 时间字段](https://info.arxiv.org/help/api/user-manual.html)、[GitHub Releases API](https://docs.github.com/en/rest/releases/releases)。

## 配音

默认使用温和的 `zh-CN-XiaoxiaoNeural` 女声，语速为 `+10%`（约1.1倍），音高降低 `8Hz`，并使用轻微暖声、齿音柔化和动态处理。可通过 `-Rate`、`-Pitch` 或 `config.json` 调整。画面保留完整标题和较丰富的摘要要点，口播使用独立的简短总结；短总结会完整读完，镜头时长由真实音频决定，不为固定时长二次变速。内容过长时应缩短口播总结，不能截断或读到一半切换；联网配音会校验词级标记与音频尾部。

视频会生成一条原创的轻松纯音乐作为背景，并在人声出现时自动压低；每条新闻切换画面时加入柔和的双段鼠标点击音效。默认混音系数分别为 `background_music_volume: 0.42` 和 `transition_click_volume: 0.32`，可以在 `config.json` 中调低或设为 `0`。输出目录会保留 `background_music.wav` 与 `transition_clicks.wav`，便于单独试听和复核。

每个新画面默认提前显示 `1.0` 秒再开始口播。中文和英文统一使用 `zh-CN-XiaoxiaoNeural`，避免切换音色造成割裂；送入语音引擎前会在 `Grok`、`ChatGPT`、`Word` 等英文名称与中文之间加入只用于发音的短停顿，画面和字幕仍显示原文。纯英文稿件也使用同一音色。可通过 `config.json` 的 `scene_lead_in_seconds` 和 `english_voice` 调整。

视频开场会先播报“欢迎来到第 X 期的 AI 日报，今天是 X 月 X 日”，再说明本期消息数量。`config.json` 的 `edition_start_date` 是第一期日期，默认为 `2026-09-21`；之后按日报日期顺延，同一天重复生成时保持一致。在输入 `briefing.json` 中设置正整数 `edition_number` 可以覆盖自动期数。

编辑稿可用 `display_title` 设置简短的画面标题，原始 `title` 仍用于来源记录和排序。`video_title` 与 `video_bullets` 用于口播总结，`bullets` 用于画面上的详细要点。

默认 `auto`：先尝试温暖、成熟的联网中文女声 `zh-CN-XiaoxiaoNeural`，失败后尝试 Windows 已安装的中文语音。联网配音会把公开的口播文字发给语音服务，不需要在本工具中填写密钥；可用性由服务决定。

`-Tts edge` 只使用联网语音；`-Tts sapi` 只使用本地语音。Windows 须已安装中文语音包，本地声音自然度低于联网语音。受限执行环境可能禁止语音引擎或网络访问，可在普通本机 PowerShell 中运行。程序不会把无声文件当作正常成片交付。

如果制作中断，已经采集的 `briefing.json` 会保留。可用 `-InputFile` 指向它重新生成，新结果将写入新目录；重新运行时仍按本次搜查日期过滤，已过期新闻不会恢复。

需要中文字体，默认使用 Windows 微软雅黑。其他环境可用 `DAILYREPORT_FONT` 指定中文字体文件；本地语音回退仅适用于 Windows。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖时间窗口、时区、去重、正文噪声过滤、摘要、字幕时间、长文本排版与安全的本地预览输出。首期成片另外经过实际语音生成与 FFmpeg 解码检查。
