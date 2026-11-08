#!/usr/bin/env bash
# 算熱點：最近 N 天 origin/main 非 merge commit 的檔案改動次數，分「全部」與「fix」兩張表。
# 用法：bash hotspots.sh [起始日 YYYY-MM-DD，預設 30 天前] [每張表印幾列，預設 30]
# 固定 ref：HOTSPOT_REF=<sha 或 ref> bash hotspots.sh …（分析期間 origin/main 前進時，結果仍可重現）
# 追加排除：HOTSPOT_NOISE='<正規式>' bash hotspots.sh …（repo 自己的產生檔或雜訊）
# 輸出本身就是報告附件：開頭印出實際用的指令，讀者可以重跑。
# 不開 pipefail：管線尾端的 head 提早關閉時，前面的 sort 會收到 SIGPIPE，整支腳本會在第一張表後中斷。
set -eu
SINCE="${1:-$(date -d '30 days ago' +%F 2>/dev/null || date -v-30d +%F)}"
TOP="${2:-30}"
# 文件、changelog、fixture、lockfile 改動很多但不是設計熱點。
NOISE='(^(changelog\.d/|CHANGELOG|docs/|tests?/fixtures/)|\.md$|(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock|poetry\.lock|Cargo\.lock|go\.sum)$)'
[ -n "${HOTSPOT_NOISE:-}" ] && NOISE="($NOISE|$HOTSPOT_NOISE)"
git fetch -q origin 2>/dev/null || true  # 離線就用本機已有的遠端 ref
MAIN="${HOTSPOT_REF:-$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)}"  # 預設 branch 不一定叫 main
# 淺複製只有最近幾個 commit，熱點會少算（pigpen 曾只剩 2 天歷史：30 天算成 39 個 commit，實際 886）。
# 淺複製最舊的邊界 commit 沒有 parent，git log 會把整棵樹算成它改的檔案，所以邊界要落在統計期間外。
# 不用 --deepen：有些 git server 會從分支頂端重切，反而把歷史砍短。
boundary_in_window() {
  [ "$(git rev-parse --is-shallow-repository)" = true ] &&
    git rev-list "$MAIN" --since="$SINCE" | grep -qFxf "$(git rev-parse --git-path shallow)"
}
if [ "$(git rev-parse --is-shallow-repository)" = true ]; then
  echo "淺複製：補抓 ${SINCE} 之前一段的歷史" >&2
  for back in 7 30 90; do
    from=$(date -d "$SINCE -$back days" +%F 2>/dev/null || date -j -v-"$back"d -f %F "$SINCE" +%F)
    git fetch -q --shallow-since="$from" origin \
      || { echo "補抓失敗（期間內可能沒有 commit，或連不到 origin）：git fetch --shallow-since=${from} origin" >&2; exit 1; }
    boundary_in_window || break
  done
  if boundary_in_window; then
    git fetch -q --unshallow origin || { echo "補抓失敗：git fetch --unshallow origin" >&2; exit 1; }
  fi
fi
BASE=$(git rev-parse --short "$MAIN")
count() { git log "$MAIN" --since="$SINCE" --no-merges "$@" --format= --name-only | grep -v '^$' | grep -vE "$NOISE" | sort | uniq -c | sort -rn | head -"$TOP"; }
echo "# 熱點（${MAIN} ${BASE}，${SINCE} 起）"
echo "commit 數：$(git log "$MAIN" --since="$SINCE" --no-merges --oneline | wc -l)，fix commit 數：$(git log "$MAIN" --since="$SINCE" --no-merges -i -E --grep='^(fix|修正|修復)' --oneline | wc -l)"
echo "排除：$NOISE"
echo
echo "## 全部改動次數"
echo "\$ git log "$MAIN" --since=$SINCE --no-merges --format= --name-only | （排除雜訊）| sort | uniq -c | sort -rn"
count
echo
echo "## fix commit 改動次數"
echo "\$ git log "$MAIN" --since=$SINCE --no-merges -i -E --grep='^(fix|修正|修復)' --format= --name-only | （排除雜訊）| sort | uniq -c | sort -rn"
count -i -E --grep='^(fix|修正|修復)'
echo
echo "## 常一起改的檔案（同一 commit，兩張表前 ${TOP} 名的聯集之間，≥3 次）"
TOPFILES=$(mktemp); trap 'rm -f "$TOPFILES"' EXIT  # BSD awk 的 -v 不收含換行的字串，改用檔案
{ count; count -i -E --grep='^(fix|修正|修復)'; } | sed -E "s/^ *[0-9]+ //" | sort -u > "$TOPFILES"
git log "$MAIN" --since="$SINCE" --no-merges --format='@%h' --name-only | grep -v '^$' \
  | awk 'FNR==NR{keep[$0]=1; next}
    /^@/{flush(); next} keep[$0]{f[++k]=$0}
    function flush(){ for(i=1;i<=k;i++) for(j=i+1;j<=k;j++){a=f[i];b=f[j]; if(a>b){x=a;a=b;b=x}; c[a" ↔ "b]++}; k=0 }
    END{flush(); for(p in c) if(c[p]>=3) print c[p], p}' "$TOPFILES" - | sort -rn | head -"$TOP"
