import json, os, subprocess, re
from pathlib import Path
p=Path('/home/ubuntu/projects/ai_dailyreport-20260927-clean/outputs/2026-10-14_101041_599115')
b=json.loads((p/'briefing.json').read_text()); t=json.loads((p/'timeline.json').read_text())
title='10.14 Gemini 4 Argon 统一百万词元额度！GLM-Legal 法律任务通过率19.2% 第24期AI日报'
desc='10.14 AI 日报 第24期｜7条速览\nGemini 4 Argon 百万词元额度、LFM2.5 本地推理、GLM-Legal、千问 Go、GPT-6 Astra 视频工作流、PAIR 本地部署、Anthropic Scion。\n完整时间轴与原文来源见评论区。企业自述不等于独立验证，内测及未来功能已明确区分。AI辅助整理与配音，原文逐条核对。'
tags='AI日报,人工智能,大模型,Gemini,GLM,千问,GPT,科技资讯'
assert len(title)<=80 and len(desc)<=250
lines=['第24期AI日报｜时间轴','00:00 开场']
for i,s in enumerate(b['stories'],1):
    seg=next(x for x in t['segments'] if x['chapter']==i and x['text'])
    secs=int(seg['start']); lines.append(f'{secs//60:02d}:{secs%60:02d} {s["title"]}')
lines.append('以上为新闻信息整理，不构成专业建议。')
sources=['原文来源（按视频顺序）：']
for i,s in enumerate(b['stories'],1):
    sources.append(f'{i}. {s["source_name"]}（{s["event_date"]}）\n'+re.sub(r'^https?://(www\.)?','',s['source_url']))
for name,text in [('bili-desc.txt',desc),('bili-timeline.txt','\n'.join(lines)),('bili-sources.txt','\n'.join(sources))]:
    assert len(text)<= (250 if name=='bili-desc.txt' else 1000), (name,len(text))
    (p/name).write_text(text)
    print(name,len(text),flush=True)
(p/'publish-metadata.json').write_text(json.dumps(dict(title=title,desc=desc,tags=tags,tid=231,copyright=1),ensure_ascii=False,indent=2))
env={k:v for k,v in os.environ.items() if k.lower() not in ('all_proxy','http_proxy','https_proxy')}
cmd=['/home/ubuntu/.venv_docx/bin/biliup','-u','/home/ubuntu/cookies.json','upload','--submit','app','--title',title,'--desc',desc,'--tag',tags,'--tid','231','--copyright','1','--cover',str(p/'cover.png'),str(p/'daily.mp4')]
r=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(p/'upload.log').write_text(r.stdout); print(r.stdout); raise SystemExit(r.returncode)
