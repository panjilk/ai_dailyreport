# -*- coding: utf-8 -*-
"""生成 10/3 期的 B站 标题/简介/评论文件并自查长度。"""
from pathlib import Path

title = "10.3 给AI配手机号和钱包！Manus 2.0 回归 第13期AI日报"

desc_lines = [
    "10.3 AI 日报 第13期｜9 条速览",
    "· Kimi K3/GLM 5.3 上架 OpenAI",
    "· Manus 2.0 与个人智能体 Cue",
    "· Anthropic 投 1 亿培训工程师",
    "· openJiuwen 模型路由",
    "· Meta Muse 登陆智能眼镜",
    "· 英伟达 64GB 版 DGX Spark",
    "· 腾讯 WorkBuddy 接入 Space Bunny",
    "· 苹果收紧 macOS 全盘访问",
    "· 谷歌 SynthID Bio 蛋白水印",
    "",
    "时间轴与来源见评论区；本视频由 AI 生成。",
]
desc = "\n".join(desc_lines)

timeline = """【第13期 AI 日报 · 2026-10-03 时间轴】
00:07 Kimi K3｜Kimi K3 与 GLM 5.3 上架 OpenAI 企业市场
00:20 Manus｜Manus 2.0 发布个人智能体 Cue
00:34 Anthropic｜Anthropic 投 1 亿美元培训工程师
00:47 openJiuwen｜首发自演进模型路由 X-Router
00:59 Meta｜Meta 把智能体 Muse 搬上智能眼镜
01:12 NVIDIA｜英伟达发布 64GB 版 DGX Spark
01:27 腾讯｜腾讯 WorkBuddy 独家接入 Space Bunny
01:41 Apple｜苹果因 AI 智能体收紧 Mac 权限
01:55 Google｜谷歌给 AI 设计的蛋白质加水印
02:09 结束"""

sources = """【本期来源 · 窗口 2026-09-29 至 2026-10-03（北京时间）】
1 Kimi K3 与 GLM 5.3 上架 OpenAI 企业市场（9月30日）IT之家 https://www.ithome.com/1/008/864.htm
2 Manus 2.0 与个人智能体 Cue（9月30日）量子位 https://www.qbitai.com/2026/09/499592.html
3 Anthropic 投 1 亿美元培训工程师（当地时间10月2日）IT之家 https://www.ithome.com/1/009/376.htm
4 openJiuwen X-Router 自演进模型路由（10月2日）量子位 https://www.qbitai.com/2026/10/500098.html
5 Meta Muse 将登陆智能眼镜（10月2日）IT之家 https://www.ithome.com/1/009/363.htm
6 英伟达 64GB 版 DGX Spark（10月2日）IT之家 https://www.ithome.com/1/009/359.htm
7 腾讯 WorkBuddy 独家接入 Space Bunny（10月2日）IT之家 https://www.ithome.com/1/009/335.htm
8 苹果收紧 macOS 全盘访问权限（10月2日）TechCrunch https://techcrunch.com/2026/10/02/apple-says-its-tightening-macos-full-disk-access-controls-due-to-new-risks-from-ai-agents/
9 谷歌 SynthID Bio 蛋白水印（9月30日）Google DeepMind https://deepmind.google/blog/introducing-synthid-bio/"""

Path('/tmp/bili_title_1003.txt').write_text(title, encoding='utf-8')
Path('/tmp/bili_desc_1003.txt').write_text(desc, encoding='utf-8')
Path('/tmp/bili_comment_1003_timeline.txt').write_text(timeline, encoding='utf-8')
Path('/tmp/bili_comment_1003_sources.txt').write_text(sources, encoding='utf-8')

print("标题", len(title), "字")
print("简介", len(desc), "字  (上限 250)")
print("时间轴评论", len(timeline), "字  (上限 1000)")
print("来源评论", len(sources), "字  (上限 1000)")
assert len(desc) <= 250, "简介超 250！"
assert len(timeline) <= 1000 and len(sources) <= 1000, "评论超 1000！"
assert len(title) <= 80
print("全部长度检查通过")
