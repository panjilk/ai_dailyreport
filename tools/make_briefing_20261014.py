import json, datetime, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
stories=[]
def add(title,nav,cat,src,url,date,evidence,bullets,voice,support=()):
    stories.append(dict(title=title,nav_label=nav,category=cat,source_name=src,source_url=url,published=date,event_date=date,event_date_evidence=evidence,verification='original_source_checked_by_editor',bullets=bullets,video_bullets=[voice],supporting_sources=[dict(name=n,url=u) for n,u in support]))
add('谷歌发布 Gemini 4 Argon，统一百万词元额度','Google','模型发布','Google Blog','https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/','2026-10-13','官方公告标注 Oct 13, 2026，并明确 today globally available；百万额度为统一输入输出上限，而非单独输出上限。',[
'10月13日，谷歌全球开放 Gemini 4 Argon；API 支持100万 token 的统一输入输出额度，面向长程编码与复杂知识任务。',
'首发价每百万输入2美元、输出10美元，缓存输入优惠95%；开发者使用付费 API，消费端面向 Pro 与 Ultra 订阅用户。',
'谷歌报告多步工作能力提升，并向1万名科学家开放六个月免费高档额度申请；需资格审核，不等于所有用户免费使用。'],
'谷歌在10月13日开放Gemini 4 Argon，接口支持输入和输出合计一百万token，适合长程编码和复杂知识任务，强调多步执行。首发每百万输入两美元、输出十美元；普通用户需要Pro或Ultra订阅，科学家免费计划也要申请审核。')
add('Liquid AI 发布 LFM2.5 本地推理模型','Liquid AI','模型发布','Liquid AI 官方博客','https://huggingface.co/blog/LiquidAI/lfm25-24b-a2b','2026-10-13','厂商博客 Published October 13, 2026；官方模型卡明确240亿总参数、24.5亿活跃参数与131072上下文。',[
'10月13日，Liquid AI 发布 LFM2.5-24B-A2B；总参数240亿，模型卡精确列出每次激活约24.5亿参数，面向本地智能体。',
'上下文扩至131072 token，并在工具调用与多步任务上训练；厂商在 M5 Max、四比特量化和4K输入条件下测得每秒184 token。',
'提供原始权重及多种部署格式，强调隐私与设备端执行；只处理文本且始终先推理，知识密集任务建议配合检索或联网搜索。'],
'Liquid AI在10月13日发布LFM2.5本地推理模型，总参数二百四十亿，每次激活约二十四点五亿，上下文超过十三万token。它能调用工具完成多步任务，但只处理文本；知识密集的工作仍建议配合检索，速度也受设备和量化设置影响。', [('官方模型卡','https://huggingface.co/LiquidAI/LFM2.5-24B-A2B')])
add('智谱发布 GLM-Legal，法律任务通过率19.2%','智谱','模型发布','智谱官方博客','https://z.ai/blog/glm-legal','2026-10-12','官方页面标注 2026-10-12；明确基于GLM-5.3-Flash、Harvey LAB all-pass为19.2%、beta申请。',[
'10月12日，智谱发布 GLM-Legal，基于 GLM-5.3-Flash 进行法律领域训练；面向合同审查、证据分析与合规研究。',
'官方披露 Harvey LAB 全条件通过率19.2%，比基础模型提高12.5个百分点；评测涉及24类法律业务，不能理解为普遍正确率。',
'API 内测需提交申请，AutoClaw 集成仍是即将提供；公告链接第三方评测结果，但专业输出仍应经过法律人员审核。'],
'智谱在10月12日发布GLM-Legal，基于GLM-5.3-Flash训练，处理合同审查、证据分析和合规研究。官方披露法律智能体评测全条件通过率百分之十九点二，比基础模型高十二点五个百分点；接口仍需申请内测，结果不能替代专业审核。')
add('GPT-6 Astra 帮 Higgsfield 制作超10分钟视频','OpenAI','产品应用','OpenAI 官方案例','https://openai.com/index/higgsfield-longer-videos-voice','2026-10-13','OpenAI RSS published=2026-10-13T12:00:00Z；正文是Higgsfield使用案例，不是当天发布GPT新版本；语音到电影是未来方向。',[
'10月13日，OpenAI 公布 Higgsfield 使用案例；该平台称接入 GPT-6 Astra 后，视频工作流由约1分钟扩至超过10分钟。',
'模型用于规划、工具调用与创作流程，团队已用它制作教学视频；同时接入 GPT-Image-2.5 处理图像，不是一次生成完整长片。',
'时长与效率来自企业自述，尚未独立复核；GPT-Live-1 支持的语音到电影是下一阶段愿景，不能写成已经上线的功能。'],
'Higgsfield在10月13日公开GPT-6 Astra创作案例，称视频工作流已从约一分钟扩展到超过十分钟，团队用于制作教学内容。关键是规划和工具调用，不是模型一次吐出整部长片；效果属于企业自述，语音生成电影仍是后续方向。')
add('阿里千问 Go 开放个人智能体体验申请','阿里','产品应用','雷峰网','https://www.leiphone.com/category/industrynews/GalDeSPl8orEfNoI.html','2026-10-13','雷峰网正文和时间栏2026-10-13 12:11，明确10月13日千问公众号公告；记者体验与用户理赔案例不是官方普遍保证。',[
'10月13日，阿里千问在 APP 内上线千问 Go 体验申请入口；这是一款个人办事智能体，并非千问基础模型新版本。',
'媒体体验列出航班延误理赔、场馆预约、餐厅预订、商品比价和求职投递等任务；目标是把问答进一步扩展为实际事务处理。',
'体验资格将逐步开放，能否完成任务受服务平台与实际授权影响；单个用户获得70元理赔的案例，不能当成通用效果承诺。'],
'阿里千问在10月13日开放千问Go体验申请，个人智能体嵌入千问应用，尝试处理航班理赔、餐厅预订、商品比价和求职投递。它是办事产品，不是基础模型升级；资格会逐步开放，具体任务能否成功，仍取决于平台支持和用户授权。')
add('Anthropic 公布 Scion，支撑日均三万次合并','Anthropic','开发生态','Anthropic','https://www.anthropic.com/engineering/redesigning-source-control','2026-10-13','工程博客 Published Oct 13, 2026；五月2500、九月超30000是历史运行数据，本条事件为当日披露内部系统设计。',[
'10月13日，Anthropic 披露内部版本控制系统 Scion；称代码日均合并从5月约2500次升至9月超过3万次，原有基础设施承压。',
'公司用五个月完成单体仓库迁移，把合并、历史查询等工作放到服务端；客户端按需取文件，适配大量持续在线的编码智能体。',
'Scion 是内部专用系统，不是 Claude 新模型，也未承诺公开提供；公司明确它不适合普遍替代 Git，中小仓库无需照搬。'],
'Anthropic在10月13日公布内部版本控制系统Scion，支撑Claude参与的大规模编码。公司日均合并量已从约两千五百次升到超过三万次，因此把合并和历史查询移到服务端。系统仅供内部使用，并不适合让普通项目直接替换Git。')
add('英伟达 PAIR 转正式版，接入 llama.cpp','NVIDIA','开发生态','NVIDIA Blog','https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/','2026-10-13','官方RSS published=2026-10-13T12:00:49Z；正文明确PAIR is officially moving out of beta today；不选10月15日才发布的Nemotron。',[
'10月13日，英伟达宣布个人 AI 路由器 PAIR 结束测试阶段；新增 llama.cpp 支持与 Hugging Face 模型直接下载。',
'工具自动发现局域网内兼容电脑、安装模型和推理引擎，并分配 AI 工作负载；支持 Windows、Linux 与 macOS。',
'这次更新针对本地模型部署和资源调度，并非新模型发布；性能取决于硬件和网络，公告中的后续模型仍未到发布日。'],
'英伟达在10月13日宣布PAIR个人AI路由器转为正式版，新增llama.cpp支持和模型直接下载。它可以发现局域网里的兼容电脑，把本地模型任务分配到不同设备，支持三种桌面系统；这是部署工具更新，速度仍受硬件和网络条件限制。')
b=dict(date='2026-10-14',window_days=5,title='AI 日报 · 2026-10-14',edition_start_date='2026-09-21',edition_note='七条原文核对的模型与开发生态更新；企业自述与未来功能明确区分。',stories=stories)
assert len(stories)==7
for s in stories:
    v=s['video_bullets'][0]
    assert len(s['title'])<=40 and len(v)<=140,(s['title'],len(v))
    assert s['source_name'] not in v or s['source_name'] in s['title']
    assert not re.search(r'http|来源|据.{0,20}(报道|消息)|…',v)
    print(s['nav_label'], 'narration chars',len(v),'CJK',len(re.findall(r'[\u4e00-\u9fff]',v)))
(ROOT/'data/briefing-2026-10-14-models.json').write_text(json.dumps(b,ensure_ascii=False,indent=2))
print('edition',(datetime.date.fromisoformat(b['date'])-datetime.date.fromisoformat(b['edition_start_date'])).days+1)
