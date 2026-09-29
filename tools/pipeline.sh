#!/usr/bin/env bash
# AI 日报一键流水线：采集 → AI改写口播 → 预检 → 生成视频
# 用法: bash tools/pipeline.sh [YYYY-MM-DD]
set -euo pipefail
cd "$(dirname "$0")/.."

PROXY="socks5h://127.0.0.1:10808"
export DEEPSEEK_API_KEY="$(cat /tmp/.ds_key)"
export ALL_PROXY="$PROXY" HTTP_PROXY="$PROXY" HTTPS_PROXY="$PROXY"

# Xray 极易中途死亡（TTS 会报 ClientProxyConnectionError）。跑前确保端口在监听，不在就自启。
ensure_proxy() {
  if ss -ltn 2>/dev/null | grep -q ':10808'; then
    echo "[代理] 10808 已在监听"
    return 0
  fi
  echo "[代理] 未监听，启动 Xray（日本节点）..."
  ( cd /tmp/xray-inst && setsid nohup ./xray run -c config-jp.json > /tmp/xray.log 2>&1 & )
  for _ in $(seq 1 20); do
    sleep 1
    if ss -ltn 2>/dev/null | grep -q ':10808'; then
      echo "[代理] 已启动"
      return 0
    fi
  done
  echo "✗ 代理启动失败，见 /tmp/xray.log"; return 1
}

ensure_proxy || exit 1

echo "===== 1/4 采集（topic_scope=$(.venv/bin/python -c "import json;print(json.load(open('config.json'))['topic_scope'])")) ====="
OUT=$(.venv/bin/python -m dailyreport --collect-only 2>&1 | tail -1 | sed 's/.*完成：//')
echo "输出目录: $OUT"
BRIEF="$(dirname "$OUT")/briefing.json"

if [ ! -f "$BRIEF" ]; then
  echo "✗ 未找到 briefing.json，采集失败"; exit 1
fi
N=$(.venv/bin/python -c "import json;print(len(json.load(open('$BRIEF'))['stories']))")
echo "采集入选: $N 条"
if [ "$N" -lt 5 ]; then
  echo "✗ 入选不足 5 条，程序会拒绝生成"; exit 1
fi

echo "===== 2/4 AI 改写口播稿（DeepSeek 直连，不走代理）====="
D="$(dirname "$BRIEF")"
env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  .venv/bin/python tools/rewrite_narration.py "$BRIEF" -o "$D/briefing-rewritten.json" 2>&1 | tail -4

echo "===== 3/4 预检 ====="
/home/ubuntu/.venv_docx/bin/python /home/ubuntu/.hermes/skills/media/ai-daily-report/scripts/precheck.py "$D/briefing-rewritten.json" 2>&1 | tail -4

echo "===== 4/4 生成视频 ====="
ensure_proxy || exit 1   # 采集耗时长，Xray 可能中途死掉，渲染前复查一次
.venv/bin/python -m dailyreport --input "$D/briefing-final.json" --tts edge 2>&1 | tail -4

echo "===== 完成 ====="
find outputs -name daily.mp4 -newermt "$(date +%Y-%m-%d) 00:00" 2>/dev/null | tail -1
