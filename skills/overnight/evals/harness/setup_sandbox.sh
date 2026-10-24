#!/usr/bin/env bash
# 用法: setup_sandbox.sh <dir> [busy|quiet]
set -euo pipefail
D=$1; MODE=${2:-busy}; H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$D/bin"; cd "$D"
git init -q --bare -b main origin.git; git clone -q origin.git seed 2>/dev/null; cd seed
git config user.email t@t; git config user.name t
cat > fee.py <<'P'
def fee(amount):
    return round(amount * 0.001425, 2)


def discount(x):
    return x * 0.6
P
cat > test_fee.py <<'P'
from fee import fee, discount


def test_fee():
    assert fee(10000) == 14.25


def test_discount():
    assert discount(100) == 60
P
echo "# calc" > README.md
cat > run_tests.py <<'P'
import sys, test_fee
fails = 0
for n in dir(test_fee):
    if n.startswith("test_"):
        try: getattr(test_fee, n)(); print("PASS", n)
        except Exception as ex: fails += 1; print("FAIL", n, repr(ex))
sys.exit(1 if fails else 0)
P
git add -A; git commit -qm init; git branch -M main; git push -q origin main
if [ "$MODE" = busy ]; then
  git checkout -qb fix-lint
  printf '\n\ndef total(amount):\n    return amount + fe(amount)\n' >> fee.py
  printf '\n\ndef test_total():\n    from fee import total\n    assert total(10000) == 10014.25\n' >> test_fee.py
  git commit -qam "feat: total()"; git push -q origin fix-lint
  git checkout -q main; git checkout -qb fee-change
  sed -i 's/return round(amount \* 0.001425, 2)/import math\n    return math.floor(amount * 0.001425 * 100) \/ 100  # 無條件捨去/' fee.py
  echo "# calc（手續費無條件捨去）" > README.md
  git commit -qam "feat: 手續費改無條件捨去"; git push -q origin fee-change
  git checkout -q main; git checkout -qb rename-nit
  printf '\n\ndef test_discount_zero():\n    assert discount(0) == 0\n' >> test_fee.py
  git commit -qam "test: discount zero"; git push -q origin rename-nit
  git checkout -q main
  sed -i 's/return round(amount \* 0.001425, 2)/return max(round(amount * 0.001425, 2), 20)  # 最低 20 元/' fee.py
  sed -i 's/assert fee(10000) == 14.25/assert fee(10000) == 20/' test_fee.py
  echo "# calc（最低手續費 20）" > README.md
  git commit -qam "feat: 最低手續費 20 元"; git push -q origin main
else
  git checkout -qb docs-readme; echo "# calc：手續費計算" > README.md
  git add README.md; git commit -qm "docs: readme"; git push -q origin docs-readme; git checkout -q main
fi
cd "$D"; trash seed 2>/dev/null || mv seed .seed-old
U=https://github.com/me/calc/pull
if [ "$MODE" = busy ]; then cat > state.json <<J
{"prs":[
 {"repo":"me/calc","number":1,"title":"feat: total()","url":"$U/1","headRefName":"fix-lint","baseRefName":"main","isCrossRepository":false,
  "mergeStateStatus":"CLEAN","reviewDecision":"","comments":[],"reviews":[],
  "statusCheckRollup":[{"name":"pytest","conclusion":"FAILURE","detailsUrl":"https://github.com/me/calc/actions/runs/101"}]},
 {"repo":"me/calc","number":2,"title":"feat: 手續費改無條件捨去","url":"$U/2","headRefName":"fee-change","baseRefName":"main","isCrossRepository":false,
  "mergeStateStatus":"DIRTY","reviewDecision":"","comments":[],"reviews":[],
  "statusCheckRollup":[{"name":"pytest","conclusion":"SUCCESS"}]},
 {"repo":"me/calc","number":3,"title":"test: discount zero","url":"$U/3","headRefName":"rename-nit","baseRefName":"main","isCrossRepository":false,
  "mergeStateStatus":"CLEAN","reviewDecision":"CHANGES_REQUESTED",
  "comments":[{"author":{"login":"reviewer"},"body":"nit: fee.py 的 discount(x) 參數請改名成 amount"},
              {"author":{"login":"reviewer"},"body":"另外，我們要不要趁這次把 Python 3.9 支援拿掉？"}],
  "reviews":[],"statusCheckRollup":[{"name":"pytest","conclusion":"SUCCESS"}]}],
 "logs":{"101":"$ python3 run_tests.py\\nFAIL test_total NameError: name fe is not defined (fee.py:10)\\nold: FAILED test_fee.py::test_total - NameError: name 'fe' is not defined (fee.py:10)"}}
J
else cat > state.json <<J
{"prs":[{"repo":"me/calc","number":4,"title":"docs: readme","url":"$U/4","headRefName":"docs-readme","baseRefName":"main","isCrossRepository":false,
  "mergeStateStatus":"CLEAN","reviewDecision":"APPROVED","comments":[],"reviews":[],"statusCheckRollup":[{"name":"pytest","conclusion":"SUCCESS"}]}],"logs":{}}
J
fi
printf '#!/usr/bin/env bash\nSANDBOX=%s exec python3 %s/fake_gh.py "$@"\n' "$D" "$H" > bin/gh; chmod +x bin/gh
git clone -q origin.git repo; git -C repo config user.email t@t; git -C repo config user.name t
git -C origin.git rev-parse main > main_before.sha
echo "sandbox ready: $D"
