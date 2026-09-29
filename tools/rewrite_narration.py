#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 DeepSeek 把自动采集的 bullets 改写成通顺的 40-60 字口播稿。

项目自带的 video_bullets 是"从原文抠句子"，论文/英文源抠出来会变成
"我们提出X""这些结果表明"这类没有主语的半截话。本脚本用大模型改写，
使口播稿像人工稿件一样通顺。

用法: python rewrite_narration.py <briefing.json> [-o 输出路径]
输出: 默认写到 <同目录>/briefing-rewritten.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

SYSTEM = """你是中文科技新闻主播的稿子编辑。把给定的新闻要点改写成一句适合口播的中文短稿。

要求：
1. 40-60 个汉字，一到两句，念出来通顺、听得懂。
2. 必须有明确主语（谁）+ 做了什么 + 关键信息（数字/能力/时间）。不能出现"我们""这些结果表明"这类没有主语的表述。
3. 忠于原文，不编造数字或结论；原文有"厂商称/官方称"等限定要保留。
4. 不要出现来源名（如"IT之家""OpenAI News"）、网址、括号标注、英文原文。
5. 直接输出改写后的中文短稿，不要任何解释、不要引号、不要换行。"""


def rewrite(story, api_key, timeout=60):
    """返回改写后的口播短稿，失败返回 None。"""
    title = str(story.get("title", ""))
    bullets = story.get("bullets") or []
    body = "\n".join(f"- {b}" for b in bullets)

    prompt = f"新闻标题：{title}\n\n要点：\n{body}"

    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 200,
        },
        timeout=timeout,
        proxies={"http": None, "https": None},  # 国内服务，绕过代理直连
    )
    resp.raise_for_status()
    out = resp.json()["choices"][0]["message"]["content"].strip()

    # 清洗：去引号、换行、来源名
    out = re.sub(r"[\r\n]+", "", out).strip('"“”\' ')
    for bad in ("IT之家", "量子位", "雷峰网", "极客公园", "OpenAI News",
                "Google DeepMind", "NVIDIA Blog", "TechCrunch"):
        out = out.replace(bad, "")
    out = re.sub(r"\s+", " ", out).strip()

    if not out or not re.search(r"[\u4e00-\u9fff]", out):
        return None
    if len(out) > 100:
        return None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefing")
    ap.add_argument("-o", "--output")
    ap.add_argument("--api-key", default=os.environ.get("DEEPSEEK_API_KEY"))
    args = ap.parse_args()

    if not args.api_key:
        print("错误：需要 DEEPSEEK_API_KEY 环境变量或用 --api-key 指定",
              file=sys.stderr)
        sys.exit(1)

    src = Path(args.briefing)
    data = json.loads(src.read_text(encoding="utf-8"))

    ok = fail = 0
    for i, story in enumerate(data["stories"], 1):
        name = str(story.get("nav_label") or story.get("title"))[:24]
        original = story.get("video_bullets")
        try:
            new = rewrite(story, args.api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"  {i}. {name:26} 调用失败: {str(exc)[:60]}")
            fail += 1
            continue

        if new is None:
            print(f"  {i}. {name:26} 改写不合格，保留原稿")
            fail += 1
            continue

        story["video_bullets"] = [new]
        print(f"  {i}. {name:26} {len(new):3}字  {new[:48]}")
        ok += 1

    out = Path(args.output) if args.output else src.with_name("briefing-rewritten.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n改写成功 {ok} 条 / 保留原稿 {fail} 条")
    print(f"已写出: {out}")


if __name__ == "__main__":
    main()
