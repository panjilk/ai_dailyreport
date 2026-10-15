import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
stories=[]
def add(title,nav,cat,src,url,date,evidence,bullets,voice,support=None):
    assert len(title)<=40 and len(voice)<=140
    stories.append(dict(title=title,nav_label=nav,category=cat,source_name=src,source_url=url,published=date,event_date=date,event_date_evidence=evidence,verification='original_source_checked_by_editor',bullets=bullets,video_bullets=[voice],supporting_sources=support or [],source_text='原文已人工核对；事实与限制见画面要点。'))
add('Meta 发布 Muse Wonder，百万上下文面向智能体','Meta','模型发布','TechCrunch','https://techcrunch.com/2026/10/12/meta-releases-its-first-frontier-model-muse-wonder/','2026-10-12','TechCrunch 正文标注 October 12, 2026，明确当日发布两款模型；VentureBeat 同日报道补充上下文与开放范围。',[
'10月12日，Meta 发布 Muse Wonder 与 Wonder Full；支持约100万 token 上下文，面向编码和长程智能体任务。',
'标准版开放 API，每百万输入与输出 token 分别收费4美元和20美元；Full 版仅向付费 Muse Code 用户提供。',
'两款模型未开放下载权重，复杂任务仍可能出错；厂商强调长期记忆与持续执行能力，不代表所有场景都优于其他模型。'],
'Meta在10月12日发布Muse Wonder系列，支持约一百万token上下文，主打长期记忆和复杂任务执行。标准版已开放接口，输入输出每百万分别收四美元和二十美元；更强的Full版只在付费编程工具中提供，权重没有开放。',[
{'name':'VentureBeat','url':'https://venturebeat.com/technology/metas-new-muse-wonder-and-muse-wonder-full-models-achieve-frontier-performance-but-only-the-weaker-one-is-available-via-api'}])
add('Python SDK 3.29 更新 Vault 与元数据过滤','OpenAI','开发生态','GitHub Release','https://github.com/openai/openai-python/releases/tag/v3.29.0','2026-10-11','官方 release 变更日志标题 3.29.0 (2026-10-11)。',[
'10月11日，OpenAI 发布 Python SDK 3.29.0，新增 Vault 更新操作与元数据过滤支持。',
'同时对齐 beta 接口的分页限制与非空参数，便于开发者管理接口调用及查询条件。',
'此次是客户端能力与文档更新，不是 GPT 新模型发布；具体服务权限和参数仍需以对应 API 文档为准。'],
'OpenAI在10月11日更新Python开发包到三点二九版，加入Vault更新和元数据过滤，方便应用管理数据与查询条件。新版还对齐测试接口的分页限制和非空参数，但这只是开发工具升级，不是GPT模型发布，使用前仍要核对接口权限。')
add('托管智能体 SDK 增加多智能体配置与工作流','Anthropic','开发生态','GitHub Release','https://github.com/anthropics/anthropic-sdk-python/releases/tag/v1.13.0','2026-10-09','GitHub releases API published_at=2026-10-09T15:28:52Z；官方变更日志列出新增项。',[
'10月9日，Anthropic 发布 Python SDK 1.13.0，向 Managed Agents 添加工作流和多智能体配置支持。',
'新增线程状态过滤，并加入 Chat 与 Cowork 统一分析指标的类型定义，帮助开发者接入管理与统计功能。',
'这次更新属于 SDK 接口支持，不代表 Claude 模型能力或价格变化；可用范围仍取决于相关服务的开放权限。'],
'Anthropic在10月9日更新Python开发包，给托管智能体增加工作流、多智能体配置和线程状态过滤。新版还补上聊天与Cowork的统一统计类型，便于开发者做管理和分析。这是接口支持升级，并非Claude新模型，实际可用范围仍受服务权限限制。')
add('铠侠开源 KV-Repurpose，缓存命中率达63.9%','铠侠','技术洞察','arXiv','https://arxiv.org/abs/2610.13060','2026-10-09','arXiv v1: 9 Oct 2026 06:17:10 UTC；HTML 首页机构 Kioxia Corporation。',[
'10月9日，铠侠公开 KV-Repurpose，基于 vLLM 研究非前缀的分段缓存复用；同一文档前面提示不同，也能尝试复用。',
'论文在特定 RAG 工作负载与30GB缓存下报告，token 命中率为63.9%，精确前缀缓存为3.3%，首个 token 等待时间降低。',
'代码采用 Apache-2.0 许可，单文档问答和摘要较稳定；跨文档推理有明显限制，结果尚不代表所有部署环境。'],
'铠侠在10月9日公开分段缓存复用方案，让同一文档即使前面的提示不同，也能尝试复用计算。论文在三十GB缓存的特定测试中，把命中率从百分之三点三提高到百分之六十三点九。不过跨文档推理仍有局限，实际收益要按业务验证。',[
{'name':'论文机构与摘要','url':'https://arxiv.org/html/2610.13060v1'}])
add('哈工大提出 CIG-SFT，按任务信息加权微调','哈工大','技术洞察','arXiv','https://arxiv.org/abs/2610.12995','2026-10-09','arXiv v1: 9 Oct 2026 04:57:55 UTC；HTML 首页机构 Harbin Institute of Technology。',[
'10月9日，哈尔滨工业大学公开 CIG-SFT，按示范 token 携带的任务条件信息分配监督微调权重。',
'方法比较冻结参考模型看到和没看到任务输入时的 token 概率，区分真正有学习价值的决策与不必要的模仿。',
'论文报告数学推理和代码生成上的泛化改进，无需新增训练数据或在线采样；目前仍是预印本结论，尚需独立复测。'],
'哈工大在10月9日提出新的监督微调方法，按每个词元包含多少任务信息来分配训练权重，减少对示范过程的机械模仿。论文报告数学推理和代码生成的泛化有所改善，不需要额外数据或在线采样；但这仍是预印本结果，效果还要独立验证。',[
{'name':'论文机构与摘要','url':'https://arxiv.org/html/2610.12995v1'}])
add('哥本哈根信息技术大学发布33语言语法评测','哥本哈根','技术洞察','arXiv','https://arxiv.org/abs/2610.13607','2026-10-09','arXiv v1: 9 Oct 2026 13:55:00 UTC；HTML 首页第一作者与多数作者为 IT University of Copenhagen。',[
'10月9日，哥本哈根信息技术大学等机构公开 BLiMPPI，用33种语言、超过1.2万组最小句对测试否定极性词的语法判断。',
'评测覆盖12个多语言模型与2个单语言模型，多语言模型在低资源语言和不能靠词频解决的句对上尤其吃力。',
'数据已公开，适合检查模型对句法与语义条件的理解；它只覆盖特定语法现象，不是综合能力排行榜，结果为论文报告。'],
'哥本哈根信息技术大学等机构在10月9日公开多语言语法评测，收录三十三种语言、超过一万两千组句子对。十四个模型的测试显示，低资源语言和需要语义判断的句子更难处理。数据已经开放，但它只测特定语法现象，不能代替综合能力排名。',[
{'name':'论文机构与摘要','url':'https://arxiv.org/html/2610.13607v1'}])
add('SCB DataX 压缩大模型反洗钱评测规模','SCB DataX','技术洞察','arXiv','https://arxiv.org/abs/2610.13627','2026-10-09','arXiv v1: 9 Oct 2026 14:09:32 UTC；HTML 首页机构 SCB DataX, SCBX Group。',[
'10月9日，SCB DataX 等公开 AMLworld-Compact，通过保留异常交易并对正常交易分层采样，降低大模型评测调用量。',
'论文在两种测试集上将目标数量压缩271倍与611倍，使用重要性权重估计完整测试集的混淆计数，召回率可精确保留。',
'精确率与 F1 仍是比率估计，保守区间较宽；七个开放权重模型在该提示设置下表现有限，不等于能替代实际金融风控。'],
'SCB DataX在10月9日公开反洗钱评测压缩方案，保留异常交易，再分层抽取正常交易，减少大模型调用。论文在两种数据集上分别把评测目标压缩二百七十一倍和六百一十一倍。不过精确率仍需估计，结果只适用于这套测试，不能当成真实风控能力。',[
{'name':'论文机构与摘要','url':'https://arxiv.org/html/2610.13627v1'}])
brief=dict(date='2026-10-13',window_days=5,title='AI 日报 · 2026-10-13',edition_start_date='2026-09-21',edition_note='精选7条未在最近3期播出的可核对更新；论文结论为作者报告，模型发布与开发工具优先。',stories=stories)
(P/'data/briefing-2026-10-13-models.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2))
print('written',len(stories))
