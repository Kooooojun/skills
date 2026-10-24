# 重構階段：從報告到合併

只有使用者在報告之後說要做，或交接單（例如 `/overnight`）明寫授權重構與合併，才進這個階段。授權範圍以使用者的原話為準：「只開 PR」就停在 PR，不合併。

一次一個重構、一個 PR。上一個 PR 合併後，main 的 push CI 要先綠，才開始合併下一個。

## 1. 開工作區

每個重構都從最新的 `origin/main` 開新 branch 和新 worktree，不動使用者正在用的 branch。

```bash
git fetch origin
git worktree add -b refactor/arch-<主題> ../arch-<主題> origin/main
```

新 worktree 通常沒有 `node_modules`、`.venv` 這類本機環境，hook 會因此失敗。照 repo 文件裝好（例如 `npm ci`），或把 hook 指到主 clone 的環境。

完整測試、build、型別檢查這類重的指令要排隊執行，記憶體小的機器同時跑兩份可能整台當掉。可以用 `flock` 搭配一個共用的鎖檔。

## 2. 先固定行為，再動結構

1. 找出擋得住行為改變的測試，改之前先跑一次，必須是綠的。
2. 現有測試不夠，就先補特徵測試，把「現況」固定住，包括現況裡看起來不對的地方。這種斷言要註明「現況（待決定）」，之後要改的人才知道這是刻意固定的，不是規格。
3. 補不出保護測試，就跳過這個重構，寫進報告。

## 3. 只改結構

- 不改口徑、門檻、業務邏輯、金額、數量、日期的計算。
- 先做減法：刪死碼、合併只有一個呼叫端的包裝，再做新形狀。
- 換 interface 時，同一個 PR 內把所有呼叫端都改掉，舊的直接刪掉，不留相容層。改名後要 grep 整個 repo（含腳本、worker、測試、字串）。
- 測試只能改「輸入的形狀」，例如 fixture 補一個新欄位、helper 改呼叫新函式。不能為了讓測試變綠去改期望值。
- 改到 AGENTS.md 標為刻意分離或有 parity test 的區域時，逐一檢查那些路徑和測試。

收攏時如果發現現況前後不一致，這個重構就一定會改到行為：

- 把它拆成兩半：「結構」那半照常做，用特徵測試固定現況，證明新舊相同。
- 「統一行為」那半另外放一個本機 branch，不 push，寫進報告給使用者決定。使用者選了之後，再開自己的 PR，照 repo 規則附 changelog。

## 4. 證明新舊相同

光說「它會編譯」不算。對有分支邏輯的重構，寫一支新舊對照腳本：

- 用 `git archive origin/main <路徑> | tar -x -C <目錄>` 取出舊版的 lib。
- 用同一批輸入（多組資料 × 多種參數，含邊緣情況）分別呼叫舊版和新版，`deepEqual` 每一個對外欄位。
- 元件裡的推導如果被搬進 lib，就在腳本裡逐字抄一份舊推導來比。
- 印出一行結果，例如 `equivalence ok: 1152 rows × 9 inputs, 88128 checks`，貼進 PR。

腳本放在報告的資料夾，不進 repo。

接著跑相關的單元測試、型別檢查，以及這區有關、但 CI 不會跑的手動 smoke。

## 5. PR

- commit 和 PR 照 repo 慣例（沒有就用 Conventional Commits，例如 `refactor(account): …`）。
- 開成 ready，不是 draft（很多 repo 的 draft 不跑 CI）。
- 純重構通常不加 changelog；會改到使用者看得到的行為才加。

PR 描述包含：

```
## 為什麼
痛點 SHA（至少 2 個）與共同根因，一兩句。

## 改了什麼邊界
刪了什麼、新的 interface、呼叫端怎麼改、測試只改了哪些輸入形狀。

## 刻意保留的現況（如果有）
哪些不一致被特徵測試固定、留給之後決定。

## 行為不變的證據
對照腳本的輸出行、測試數字、型別檢查、跑過哪些 smoke、沒跑哪些。

## 範圍
動到哪些檔案；沒碰錢、時間、權限規則；為什麼不加 changelog。
```

## 6. 合併前的 review 關卡

前提條件，任一條不符就不要叫 reviewer：

- CI 的必要關卡都是 `completed`／`success`，而且對應目前的 PR head。
- CI 跑完後 main 有新 commit 時，照 repo 規則判斷要不要先整合 main 再重跑。
- 沒有人類 reviewer 還沒回答的問題。

派一個全新的 agent 當 reviewer。只讀，不給它你的結論。給它的資料：

- 要做的動作：merge PR #N，不部署。
- PR 連結、本機路徑與 head SHA、`AGENTS.md` 路徑、怎麼自己核對 CI。
- PR 宣稱的不變條件，請它自己驗證，例如「X 回傳值與 origin/main 一致」「沒有人再讀 Y」。
- 對照腳本的路徑：可以讀、可以跑、可以質疑涵蓋範圍，但不要只信它。
- BLOCK 條件：
  - 碰到錢、時間、權限、資料的計算規則。
  - 為了變綠改了測試期望值，但 PR 沒有說明。
  - schema、auth、secret、刪資料。
  - 動到別人的 branch。
  - CI 不對應目前的 head。
- 最後一行只回 `PASS` 或 `BLOCK：<原因>`。

看結果：

- **PASS**：reviewer 提到的小缺口（例如少一條斷言）如果補起來很便宜，就補。補了等於新的 head，要重跑 CI，再派一個新的 reviewer。
- **BLOCK**：能修就修，修完派新的 reviewer。同一件事被 BLOCK 兩次，就停下來交給使用者。

## 7. 合併與合併後

```bash
gh pr merge <N> --squash --match-head-commit <reviewed-head-sha>
```

- 用 squash（repo 不允許時照它的規則）。`--match-head-commit` 確保合進去的就是 review 過的那個 head。
- 合併後讀回 `gh pr view <N> --json state,mergeCommit`，確認真的合了。
- 等 main 的 push CI 跑完：
  - 綠了，才合併下一個 PR。
  - 紅了，馬上開 revert PR（`git revert <squash sha>`），同樣過 CI 和 review，並停止合併其他 PR。
- squash 合併後本機 branch 用 `git branch -d` 刪不掉；不要用 `-D` 強刪，留給使用者自己處理。worktree 用 `git worktree remove` 收掉。

不部署。部署由使用者自己做。
