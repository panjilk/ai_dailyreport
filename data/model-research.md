# 大模型迭代与效果：来源核验

核验截至2026-09-12，收录4条；时间范围为2026-09-01至2026-09-12，共12个自然日，不是过去24小时快讯。只收录模型版本、能力变化和可核实的效果，不沿用旧稿中的基础设施、手表、金融观点或产品协作新闻。

## 来源与日期

| 导航 | 主要来源 | 日期处理 |
| --- | --- | --- |
| ChatGPT | [OpenAI：GPT-6 Astra工作能力介绍](https://openai.com/index/gpt-6-astra-next-generation-work/) | published记2026-09-09，为该介绍文章日期；正文明确模型此前已推出，不将9月9日写成首发日。官方[新闻索引](https://openai.com/news/)确认文章日期；独立机构[模型记录](https://artificialanalysis.ai/models/gpt-6-astra)记首发为9月3日。 |
| Claude | [Anthropic：Fable 5.1与Mythos 5.1](https://www.anthropic.com/claude-fable-and-mythos-5-1) | published记2026-09-01；[官方新闻索引](https://www.anthropic.com/news)提供具体日期，发布页标注2026年9月。 |
| Gemini | [Google：Gemini 3.8 Flash与Flash Cyber](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) | 英文发布页明确2026-09-02，使用该日期，未混用地区译文日期。 |
| DeepSeek | [DeepSeek：V4.1 Flash](https://deepseek.com/news/deepseek-v4-1-flash/) | 官方发布页明确2026-09-10；9月14日中午的Pro接口切换属于未来安排，不写成已生效。 |

published使用ISO日期字符串，保留来源可核实的日级精度，不虚构小时、分钟或时区。根对象window_days为12（最终稿移除window_hours，以自然日期范围展示），用于标识扩展选题范围，不宣称已完整观测9月12日全天。

## 效果证据与归因

1. **ChatGPT：官方定义升级方向，独立测评确认提升及退步。** [Artificial Analysis于9月9日发布的评测](https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra)是正文中AA的全名及出处。智能指数53、前代47；编程智能体指数62、前代55。使用最高推理档，编程结果对应Codex环境；任务成本比前代约高15%。呈现质量下降来自同一文章的AA-Briefcase分析。未把厂商单项测试与AA分数混成一套结果。

2. **Claude：厂商自测与独立结果分别呈现。** 官方表格的Terminal-Bench 4.0中，Fable 5为42.0%，Fable 5.1为55.8%；这是厂商运行公开基准的结果，并非独立复测。上条所链AA文章另给出Fable 5.1在max with fallback设置下智能指数53。两个品牌的53分属于同一篇报告的同一指数；不据此宣布所有能力相同。Mythos访问限制取自官方发布说明。

3. **Gemini：仅引用官方公布的效果。** 官方HLE-Verified成绩54.9%；正文译为“经核验的人类终极考试”，不与未核验版HLE或AA智能指数直接比较。长任务表现、较高推理投入可能增加词元消耗，以及普通版与防御版的访问区别均来自发布说明。本次未取得足以纳入正文的独立复测，故明确写为厂商结果，没有把合作方证言或外部基准名称当作独立验证。

4. **DeepSeek：官方架构变更搭配独立测量。** [AA模型页](https://artificialanalysis.ai/models/deepseek-v4-1-flash)在本次访问中显示max推理模式智能指数40、每项指数任务加权平均费用0.27美元，并指出输出冗长。指数使用v4.3口径；费用不是每百万词元单价，也不是任意实际任务报价。视觉能力与超过V4 Pro的表述归于官方；AA综合指数不等于对每项视觉能力的复现。本次未使用波动较大的输出速度数字。

AA属于模型厂商之外的评测机构；以上“独立”描述其测量来源，不意味着完全无商业关系、结果无条件适用于生产，或已由本项目再次运行验证。不同推理设置、工具框架、基准版本与任务分布会影响结果。没有运行本地模型测评。

## 筛选与阅读记录

已检索并打开各品牌官方发布页、官方索引及所引用的独立评测原页。OpenAI、Anthropic另通过requests读取页面正文核对；不以搜索结果摘要替代已引用文章。OpenAI模型身份还与[官方API文档](https://developers.openai.com/api/docs/models/gpt-6-astra)交叉检查。

GLM线索已找到，但本版优先完成四条已充分核实的内容：[官方ZCode更新日志](https://zcode.z.ai/en/changelog)显示8月26日已加入GLM-5.3-Flash，而[AutoClaw介绍页](https://autoclaw.z.ai/blog/model/glm-5.3-flash/)标注9月11日，不能把后续介绍日期当成首次模型发布日；主发布博客本次未返回可读正文。此为本版未纳入的原因，不表示GLM没有更新。没有为了补齐品牌编造条目。

## 数据检查

输出为`data/briefing-2026-09-12-models.json`，根对象沿用complete稿字段，新增新闻各自的nav_label；清空与本次选题无关的旧collection_errors。summary_mode继续为editorial_complete。evidence是要点的编辑性转述，不是逐字引用；verification区分“官方加独立评测”与“仅官方评测”。

| 导航 | 标题码点数 | 正文码点数 | 要点数 |
| --- | ---: | ---: | ---: |
| ChatGPT | 17 | 204 | 3 |
| Claude | 23 | 217 | 3 |
| Gemini | 22 | 199 | 3 |
| DeepSeek | 26 | 210 | 3 |

字符数包括标点及英文数字。每条恰好3个完整中文句子，全部以中文句号结束，标题均少于30个Unicode码点，无换行或省略截断。逐条重读JSON核验`narration == title + '。' + ''.join(bullets)`，检查不可见控制字符、替换字符与省略号。无segments，每条对应一个内容页；本次不运行或修改渲染、语音和视频代码，因此没有声称完成像素级排版验证。

本次只写入本记录与模型JSON两个数据文档。

最终整合：category映射为程序分类“模型发布”；补充supporting_sources，让独立评测链接随文字日报交付。
