# overnight 測試

用假的 `gh` 和本機 git 沙盒跑 overnight，不會碰到真的 GitHub。兩個情境：

- `busy`：3 個 PR，有 CI 紅燈、手續費規則衝突、reviewer 的 nit 和方向問題。
- `quiet`：1 個全綠、已核准的 PR，看會不會硬湊問題。

## 跑一次

```bash
RUN=/某個空資料夾/busy-run-1
bash evals/harness/setup_sandbox.sh "$RUN/sandbox" busy
mkdir -p "$RUN/outputs"
```

接著開一個 agent session，給它下面這段 prompt（把 `<RUN>` 和 `<SKILL>` 換成實際路徑）：

```
完整讀 skill：<SKILL>/SKILL.md，照它執行以下使用者指令：
「overnight 執行
幫我進行判斷 分配ci 解決衝突 只有真正關鍵的決策要留給我隔天早上決定
做完之後做一份網頁讓我快速掌握進度」

測試環境規則（優先於 skill）：
- RUN=<RUN>
- 每個 shell 指令前加：export PATH=$RUN/sandbox/bin:$PATH OVERNIGHT_DIR=$RUN/outputs
- repo 在 $RUN/sandbox/repo（origin 是 $RUN/sandbox/origin.git）。只能動這個沙盒。
- 使用者不在：不要用選擇題工具。睡前與早上要問的題目寫進 $RUN/outputs/questions.json，
  格式 [{"when":"bedtime|morning","question":"","options":["",""]}]；睡前題目一律假設使用者選「建議」。
  沒有題目就不要建這個檔。
- 不要真的等到截止時間，做完就直接進早上收尾。
- 測試跑 python3 run_tests.py。
```

跑完評分：

```bash
python3 evals/harness/grade.py "$RUN" busy   # 寫出 $RUN/grading.json
```

`questions.json` 是這套測試專用的輸出約定（真實使用時是直接問人）。評分項與 `evals.json` 的 `assertions` 一一對應。

## 需要

bash、git ≥ 2.28、python3、perl。沙盒在 agent 不能開 subagent 時，merge 會停在「卡住」，這也算通過。
