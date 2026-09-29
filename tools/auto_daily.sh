#!/usr/bin/env bash
# AI 日报全自动流水线：采集 -> Codex 编稿 -> 预检 -> 渲染 -> 验证
# 用法: bash tools/auto_daily.sh
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"
export DEEPSEEK_API_KEY="$(cat /tmp/.ds_key 2>/dev/null || echo '')"
SOCKS="socks5h://127.0.0.1:10808"
HTTPP="http://127.0.0.1:10809"

log() { echo "[auto_daily] $*"; }

ensure_xray() {
  if ss -ltn 2>/dev/null | grep -q ':10808' && ss -ltn 2>/dev/null | grep -q ':10809'; then
    log "代理已在监听 (10808/10809)"; return 0
  fi
  log "启动 Xray（日本节点）..."
  ( cd /tmp/xray-inst && setsid nohup ./xray run -c config-jp.json > /tmp/xray.log 2>&1 & )
  for _ in $(seq 1 20); do
    sleep 1
    if ss -ltn 2>/dev/null | grep -q ':10808'; then log "代理已就绪"; return 0; fi
  done
  log "✗ 代理启动失败，见 /tmp/xray.log"; return 1
}

verify_video() {
  local f="$1"
  ffprobe -v error -show_entries format=duration \
    -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 "$f"
  ffmpeg -hide_banner -i "$f" -af volumedetect -f null /dev/null 2>&1 \
    | grep -E "mean_volume|max_volume" || true
}

ensure_xray || exit 1

# ---------- 1/5 采集 ----------
export ALL_PROXY="$SOCKS" HTTP_PROXY="$SOCKS" HTTPS_PROXY="$SOCKS"
log "===== 1/5 采集新闻 ====="
COLLECT_OUT="$(.venv/bin/python -m dailyreport --collect-only 2>&1 | tail -1)"
D="$(echo "$COLLECT_OUT" | sed 's/.*完成：//' | xargs dirname || true)"
BRIEF="$D/briefing.json"
if [ ! -f "$BRIEF" ]; then log "✗ 未找到 $BRIEF"; exit 1; fi
N=$(python3 -c "import json;print(len(json.load(open('$BRIEF'))['stories']))")
log "采集入选 $N 条 -> $BRIEF"
if [ "$N" -lt 3 ]; then log "✗ 候选过少（$N 条），本轮放弃"; exit 1; fi

# ---------- 2/5 Codex 编稿 ----------
log "===== 2/5 Codex 编稿（按 tools/EDITOR_GUIDE.md）====="
AUTHORED="$D/briefing-authored.json"
export ALL_PROXY="$HTTPP" HTTP_PROXY="$HTTPP" HTTPS_PROXY="$HTTPP"
unset NO_PROXY no_proxy || true

codex exec -C "$PWD" --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
"你是 AI 日报的主编。请按 tools/EDITOR_GUIDE.md 的规范，把采集结果编成一份可直接口播的稿件。

输入：$BRIEF
输出：$AUTHORED（合法 JSON，UTF-8）

要求：
1. 先读 tools/EDITOR_GUIDE.md 了解选题标准和口播稿要求
2. 读输入文件，只剔除【明确无关】的条目（游戏、硬件外设、流媒体算法、非 AI 论文、工具版本号）。**大模型相关的论文、评测基准、安全/事故消息要保留**。编辑后条数**不得少于 5 条**——少于 5 条项目会拒绝出片；采到的候选本就不多，判不准就保留，绝不因"感觉不够好"而砍到 5 条以下
3. 保留条目的 title 改成简洁明确的表述（要具体到机构，不写「研究团队」）；为每条写 video_bullets（40-70 字，必须有主语+事件+关键数字，不得编造）。video_bullets 里**严禁出现「据报道」「据…消息」「来源」「http」等转载句式**——渲染器会直接拒绝出片
4. 逐条核对 nav_label（重要）：填【模型所属厂商或论文作者单位】——这是哪家的东西，不是使用方、不是来源站、不是模型名。GPT 一律写 OpenAI（新闻说「爱彼迎用 GPT-6」，标签仍是 OpenAI）；Whisper 也是 OpenAI；Hunyuan→腾讯、GLM→智谱、LongCat→美团、MiMo→小米、Gemini→Google。**严禁写「研究团队」「研究人员」「作者」这类空标签**——论文类必须查出作者单位（摘要里有线索就用；没有就抓 arxiv.org/html/<id>v1 或 pdf 首页作者块的 Affiliation），多个单位取第一/通讯作者单位或出现最多的单位。标题也要具体，不要写「研究团队提出X」
5. 清洗 bullets：机翻残留（英文残留、缺标点、网页噪音如「你的浏览器不支持…」）必须重写成通顺中文或删除；每条 bullets 必须有标点且首段 ≤76 字，否则渲染会整条剔除该新闻
6. 保留原始 source_url 不变
7. 把结果写成 $AUTHORED，顶层结构与输入一致
8. 完成后用 python3 -c 验证该文件是合法 JSON，并打印保留了几条、每条的 nav_label

只做这一件事，不要修改其它文件。" || { log "✗ Codex 编稿失败"; exit 1; }

[ -f "$AUTHORED" ] || { log "✗ Codex 未产出 $AUTHORED"; exit 1; }
AN=$(python3 -c "import json;print(len(json.load(open('$AUTHORED'))['stories']))" 2>/dev/null || echo 0)
log "编稿完成，保留 $AN 条"
if [ "$AN" -lt 3 ]; then log "✗ 编稿后条数过少（$AN）"; exit 1; fi

# ---------- 3/5 预检 ----------
log "===== 3/5 预检 ====="
PRE="/home/ubuntu/.hermes/skills/media/ai-daily-report/scripts/precheck.py"
if [ -f "$PRE" ]; then
  /home/ubuntu/.venv_docx/bin/python "$PRE" "$AUTHORED" 2>&1 | tail -3
else
  cp "$AUTHORED" "$D/briefing-final.json"
fi
FINAL="$D/briefing-final.json"
[ -f "$FINAL" ] || { log "✗ 预检未产出 $FINAL"; exit 1; }

# ---------- 4/5 渲染 ----------
log "===== 4/5 渲染视频 ====="
export ALL_PROXY="$SOCKS" HTTP_PROXY="$SOCKS" HTTPS_PROXY="$SOCKS"
.venv/bin/python -m dailyreport --input "$FINAL" --tts edge 2>&1 | tail -3

# ---------- 5/5 验证 ----------
VID="$(find outputs -name daily.mp4 -newermt "$(date +%Y-%m-%d) 00:00" 2>/dev/null | tail -1)"
if [ -z "$VID" ]; then log "✗ 未找到成片"; exit 1; fi
log "===== 5/5 验证 ====="
verify_video "$VID"
DEST="/home/ubuntu/ai_daily_$(date +%Y%m%d).mp4"
cp "$VID" "$DEST"
cp "$(dirname "$VID")/cover.png" "/home/ubuntu/ai_daily_$(date +%Y%m%d)_cover.png" 2>/dev/null || true
log "✅ 成片: $VID"
log "✅ 已复制: $DEST"
