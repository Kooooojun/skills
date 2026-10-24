#!/usr/bin/env bash
# 算熱點：最近 N 天 origin/main 非 merge commit 的檔案改動次數，分「全部」與「fix」兩張表。
# 用法：bash hotspots.sh [起始日 YYYY-MM-DD，預設 30 天前] [每張表印幾列，預設 30]
# 追加排除：HOTSPOT_NOISE='<正規式>' bash hotspots.sh …（repo 自己的產生檔或雜訊）
# 輸出本身就是報告附件：開頭印出實際用的指令，讀者可以重跑。
# 不開 pipefail：管線尾端的 head 提早關閉時，前面的 sort 會收到 SIGPIPE，整支腳本會在第一張表後中斷。
set -eu
SINCE="${1:-$(date -d '30 days ago' +%F 2>/dev/null || date -v-30d +%F)}"
TOP="${2:-30}"
# 文件、changelog、fixture、lockfile 改動很多但不是設計熱點。
NOISE='(^(changelog\.d/|CHANGELOG|docs/|tests?/fixtures/)|\.md$|(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock|poetry\.lock|Cargo\.lock|go\.sum)$)'
[ -n "${HOTSPOT_NOISE:-}" ] && NOISE="($NOISE|$HOTSPOT_NOISE)"
git fetch -q origin main
BASE=$(git rev-parse --short origin/main)
count() { git log origin/main --since="$SINCE" --no-merges "$@" --format= --name-only | grep -v '^$' | grep -vE "$NOISE" | sort | uniq -c | sort -rn | head -"$TOP"; }
echo "# 熱點（origin/main $BASE，$SINCE 起）"
echo "commit 數：$(git log origin/main --since="$SINCE" --no-merges --oneline | wc -l)，fix commit 數：$(git log origin/main --since="$SINCE" --no-merges -i --grep='^fix' --oneline | wc -l)"
echo "排除：$NOISE"
echo
echo "## 全部改動次數"
echo "\$ git log origin/main --since=$SINCE --no-merges --format= --name-only | （排除雜訊）| sort | uniq -c | sort -rn"
count
echo
echo "## fix commit 改動次數"
echo "\$ git log origin/main --since=$SINCE --no-merges -i --grep='^fix' --format= --name-only | （排除雜訊）| sort | uniq -c | sort -rn"
count -i --grep='^fix'
echo
echo "## 常一起改的檔案（同一 commit，兩張表前 $TOP 名的聯集之間，≥3 次）"
TOPFILES=$( { count; count -i --grep='^fix'; } | awk '{print $2}' | sort -u)
git log origin/main --since="$SINCE" --no-merges --format='@%h' --name-only | grep -v '^$' \
  | awk -v top="$TOPFILES" 'BEGIN{n=split(top,t,"\n"); for(i=1;i<=n;i++) keep[t[i]]=1}
    /^@/{flush(); next} keep[$0]{f[++k]=$0}
    function flush(){ for(i=1;i<=k;i++) for(j=i+1;j<=k;j++){a=f[i];b=f[j]; if(a>b){x=a;a=b;b=x}; c[a" ↔ "b]++}; k=0 }
    END{flush(); for(p in c) if(c[p]>=3) print c[p], p}' | sort -rn | head -"$TOP"
