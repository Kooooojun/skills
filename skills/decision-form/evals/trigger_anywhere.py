"""觸發測試（整段版，會花 claude -p 額度）：skill-creator 的 run_eval.py 只看第一個工具呼叫，
宿主有 SessionStart hook 時 Claude 常先查資料才叫 skill，會被誤判成沒觸發。
這裡改看整段：叫到本 skill 算觸發；叫到別的 skill、跑完都沒叫算沒觸發；出錯或逾時算失敗。
Bash 與寫入類工具都停用，測試不會真的動手。

用法（在任意空資料夾執行，會在該處建 .claude/commands/ 暫存檔，跑完刪掉）：
    python3 trigger_anywhere.py <trigger-evals.json> <skill 資料夾> [每題次數]
"""

import json
import os
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

STOP_TOOLS = {"Write", "Edit", "NotebookEdit", "Artifact"}
# 測試只看會不會叫 skill，不讓它真的動手：寫入類工具與 Bash 一律停用（本機可能是 bypassPermissions）。
DISALLOWED = "Bash Write Edit NotebookEdit Artifact WebFetch"
MAX_TOOLS, MAX_TURNS, TIMEOUT = 25, 12, 240


def description(skill: Path) -> str:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("description:"))
    return line.split(":", 1)[1].strip()


def run_one(query: str, desc: str) -> str:
    name = f"decision-form-skill-{uuid.uuid4().hex[:8]}"
    cmd_file = Path(".claude/commands") / f"{name}.md"
    cmd_file.parent.mkdir(parents=True, exist_ok=True)
    cmd_file.write_text(f"---\ndescription: |\n  {desc}\n---\n\n# decision-form\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proc = subprocess.Popen(["claude", "-p", query, "--output-format", "stream-json", "--verbose",
                             "--disallowedTools", DISALLOWED, "--max-turns", str(MAX_TURNS),
                             "--strict-mcp-config"],  # 不給 --mcp-config＝不載入任何 MCP，避免真的寫進 Notion 等服務
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
    # 靜默卡住時 stdout 不會有新行，迴圈裡檢查時間沒用，改由計時器砍掉。
    timer = threading.Timer(TIMEOUT, proc.kill)
    timer.start()
    verdict, tools, events = None, 0, 0
    try:
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            events += 1
            if ev.get("type") == "result":
                # 跑完都沒叫 skill；登入失效、限流等錯誤結果不能當成「沒觸發」而讓反例空洞通過。
                done = ev.get("subtype") in ("success", "error_max_turns")  # 回合用完也是沒叫 skill
                verdict = "no-skill" if done else f"error:{ev.get('subtype')}"
                break
            if ev.get("type") != "assistant":
                continue
            for c in ev["message"]["content"]:
                if c.get("type") != "tool_use":
                    continue
                tools += 1
                if c["name"] == "Skill":
                    # 平行執行時同資料夾有多份暫存檔，本機也可能已裝正式版；叫到任何一份都算本 skill。
                    skill = c["input"].get("skill", "")
                    verdict = "TRIGGERED" if "decision-form" in skill else f"other:{skill}"
                elif c["name"] in STOP_TOOLS or c["name"].startswith("mcp__") or tools > MAX_TOOLS:
                    verdict = f"stop:{c['name']}"
                else:
                    continue
                break
            else:
                continue
            break
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()
        cmd_file.unlink(missing_ok=True)
    if verdict is None:
        verdict = "timeout" if events else f"error:no-output rc={proc.returncode}"
    return verdict


def main() -> None:
    evals = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    desc = description(Path(sys.argv[2]))
    runs = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    jobs = [(e, i) for e in evals for i in range(runs)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        verdicts = list(pool.map(lambda j: run_one(j[0]["query"], desc), jobs))
    passed = 0
    for e in evals:
        vs = [v for (ee, _), v in zip(jobs, verdicts) if ee is e]
        hit = sum(v == "TRIGGERED" for v in vs)
        broken = any(v.startswith(("error", "timeout")) for v in vs)
        ok = not broken and (hit / len(vs) >= 0.5) == e["should_trigger"]
        passed += ok
        print(f"{'✅' if ok else '❌'} 應觸發={e['should_trigger']} {hit}/{len(vs)} {vs} {e['query'][:36]}")
    print(f"{passed}/{len(evals)} 通過")
    sys.exit(0 if passed == len(evals) else 1)


if __name__ == "__main__":
    main()
